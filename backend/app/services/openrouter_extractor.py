import json
import re
import logging
import httpx
import time
from typing import Any
from app.config import Settings
from app.services.extractor import VisionExtractor, ExtractionError

logger = logging.getLogger(__name__)

class OpenRouterExtractor(VisionExtractor):
    """
    Vision extractor backed by OpenRouter's OpenAI-compatible API.

    Contract:
        `image_b64` is ALWAYS a data-URL ("data:image/jpeg;base64,...") produced
        by `preprocessor.preprocess_to_base64`. Never pass a raw base64 string.
    """

    def __init__(self, settings: Settings):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.invoke_url = "https://openrouter.ai/api/v1/chat/completions"
        logger.info(f"OpenRouterExtractor initialized with model: {self.model}")

    @property
    def source(self) -> str:
        return "openrouter"

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
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "AutoMTO",
            "Content-Type": "application/json"
        }

        # image_b64 is always a data-URL from preprocessor — passed through as-is.

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
            "response_format": {"type": "json_object"}
        }

        attempts = 3
        for attempt in range(attempts):
            try:
                logger.info(f"OpenRouter API request attempt {attempt + 1}/{attempts} (model: {self.model})")
                start_time = time.time()
                with httpx.Client(timeout=90.0) as client:
                    response = client.post(self.invoke_url, headers=headers, json=payload)
                elapsed = time.time() - start_time
                logger.info(f"OpenRouter response received in {elapsed:.2f}s with status code {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    error_info = result["error"]
                    err_msg = error_info.get("message", "Unknown error")
                    err_code = error_info.get("code")
                    raise ExtractionError(f"OpenRouter API error (code {err_code}): {err_msg}")
                
                if "choices" not in result or len(result["choices"]) == 0:
                    logger.error(f"OpenRouter invalid response structure: {result}")
                    raise ExtractionError("OpenRouter returned invalid API structure.")
                    
                content = result["choices"][0]["message"]["content"]
                
                # Try to parse the JSON string from the response
                try:
                    content_str = content.strip()
                    start_idx = -1
                    for fence in ["```json", "```JSON", "```"]:
                        idx = content_str.find(fence)
                        if idx != -1:
                            start_idx = idx
                            content_str = content_str[idx + len(fence):].strip()
                            break
                    if start_idx != -1:
                        end_idx = content_str.find("```")
                        if end_idx != -1:
                            content_str = content_str[:end_idx].strip()
                    
                    parsed_data = json.loads(content_str)
                except json.JSONDecodeError as e:
                    raise ExtractionError(f"Failed to parse OpenRouter response as JSON: {str(e)}")
                
                # Validate the basic structure exists
                if "drawing_meta" not in parsed_data or "items" not in parsed_data:
                    raise ValueError("JSON response missing required keys 'drawing_meta' or 'items'")
                    
                return parsed_data
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying OpenRouter in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"OpenRouter extraction failed after {attempts} attempts: {str(e)}")
                    raise ExtractionError(f"OpenRouter extraction failed after {attempts} attempts: {str(e)}") from e
