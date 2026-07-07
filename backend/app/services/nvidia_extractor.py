import json
import logging
import time
import httpx
from typing import Any
from app.config import Settings
from app.services.extractor import VisionExtractor, ExtractionError

logger = logging.getLogger(__name__)

class NvidiaExtractor(VisionExtractor):
    def __init__(self, settings: Settings):
        self.api_key = settings.nvidia_api_key
        self.model = settings.nvidia_model
        
        # Normalize the base URL
        base_url = settings.nvidia_base_url.strip()
        if "/chat/completions" in base_url:
            self.invoke_url = base_url
        else:
            self.invoke_url = f"{base_url.rstrip('/')}/chat/completions"
        logger.info(f"NvidiaExtractor initialized with invoke_url: {self.invoke_url} and model: {self.model}")


    @property
    def source(self) -> str:
        return "nvidia"

    def extract(self, image_b64: str, ocr_context: str = "") -> dict[str, Any]:
        prompt = (
            "You are a piping engineering AI assistant. Analyze the uploaded piping isometric drawing (drawing image) "
            "and extract a structured Material Take-Off (MTO). "
            "Your output must be a single JSON object containing 'drawing_meta' and 'items'.\n\n"
            "CRITICAL RULES:\n"
            "1. Categories MUST be one of: ['PIPE', 'FITTING', 'FLANGE', 'VALVE', 'SUPPORT', 'WELD'].\n"
            "2. DO NOT extract GASKET or BOLT rows — these are programmatically derived later. Ignore them.\n"
            "3. For PIPE items, do NOT calculate total length. Instead, extract 'segment_lengths' as a list of numbers representing the individual pipe segment dimensions shown on the drawing (e.g. [1178, 1476]). Keep 'quantity' as 0.\n"
            "4. NPS Sizes must include double quotes (e.g. \"6\\\"\" or \"6\\\"x4\\\"\").\n"
            "5. Material specs should use ASME/ASTM vocabulary (e.g., 'ASTM A106 Gr.B', 'ASTM A234 WPB', 'ASTM A105', etc.).\n"
            "6. Read the title block for 'drawing_meta': drawing_no, revision, line_number, nps, material_class, service, design_pressure, design_temperature.\n"
            "7. If a value is not explicitly written on the drawing, return `null` or `Unknown`. DO NOT guess or infer material specs, pressures, or drawing numbers.\n"
            "8. Return ONLY valid JSON matching this schema:\n"
            "{\n"
            "  \"drawing_meta\": {\n"
            "    \"drawing_no\": \"string\",\n"
            "    \"revision\": \"string\",\n"
            "    \"line_number\": \"string\",\n"
            "    \"nps\": \"string\",\n"
            "    \"material_class\": \"string\",\n"
            "    \"service\": \"string\",\n"
            "    \"design_pressure\": \"string or null\",\n"
            "    \"design_temperature\": \"string or null\"\n"
            "  },\n"
            "  \"items\": [\n"
            "    {\n"
            "      \"item_no\": 1,\n"
            "      \"category\": \"PIPE | FITTING | FLANGE | VALVE | SUPPORT | WELD\",\n"
            "      \"description\": \"ASME specification description (e.g., '90 Deg LR Elbow, BW, ASME B16.9')\",\n"
            "      \"size_nps\": \"string\",\n"
            "      \"schedule_rating\": \"string or null (e.g., 'SCH 40', 'CL150')\",\n"
            "      \"material_spec\": \"string or null (e.g., 'ASTM A234 WPB')\",\n"
            "      \"end_type\": \"BW | SW | THD | FLGD | null\",\n"
            "      \"quantity\": 12.45,\n"
            "      \"segment_lengths\": [1178, 1476],\n"
            "      \"confidence\": 0.9,\n"
            "      \"remarks\": \"string\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "FEW-SHOT EXAMPLE (MISSING BOM):\n"
            "If the drawing lacks a Bill of Materials table entirely, rely strictly on text written on the page. Do not hallucinate specs. Return `null` for material_spec and schedule_rating. For drawing metadata, if it is not printed, return `Unknown`."
        )

        if ocr_context:
            prompt += f"\n\n{ocr_context}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Format image for Llama 3.2 Vision NIM API
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_b64
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.20,  # Low temperature for deterministic output
            "top_p": 1.00,
            "response_format": {"type": "json_object"}
        }

        # Attempt extraction with retries and exponential backoff
        attempts = 3
        for attempt in range(attempts):
            try:
                logger.info(f"NVIDIA API request attempt {attempt + 1}/{attempts} (model: {self.model})")
                start_time = time.time()
                with httpx.Client(timeout=90.0) as client:
                    response = client.post(self.invoke_url, headers=headers, json=payload)
                elapsed = time.time() - start_time
                logger.info(f"NVIDIA response received in {elapsed:.2f}s with status code {response.status_code}")
                
                if response.status_code != 200:
                    raise ExtractionError(
                        f"NVIDIA Build API returned status {response.status_code}: {response.text}"
                    )
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse output as JSON
                parsed_data = json.loads(content)
                
                # Check top-level keys
                if "drawing_meta" not in parsed_data or "items" not in parsed_data:
                    raise ValueError("JSON response missing required keys 'drawing_meta' or 'items'")
                
                return parsed_data
                
            except ExtractionError:
                # Already a terminal failure — don't retry
                raise
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying NVIDIA in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"NVIDIA Build extraction failed after {attempts} attempts: {str(e)}")
                    raise ExtractionError(f"NVIDIA Build extraction failed after {attempts} attempts: {str(e)}") from e
