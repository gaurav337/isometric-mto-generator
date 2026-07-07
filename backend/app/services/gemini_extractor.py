import base64
import json
import logging
import time
from typing import Any
from google import genai
from google.genai import types
from app.config import Settings
from app.services.extractor import VisionExtractor, ExtractionError

logger = logging.getLogger(__name__)

class GeminiExtractor(VisionExtractor):
    def __init__(self, settings: Settings):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"GeminiExtractor initialized with model: {self.model_name}")

    @property
    def source(self) -> str:
        return "gemini"

    def extract(self, image_b64: str) -> dict[str, Any]:
        # Decode the image_b64 to raw bytes and parse the mime type
        try:
            if "," in image_b64:
                header, encoded = image_b64.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
            else:
                encoded = image_b64
                mime_type = "image/jpeg"
            
            image_bytes = base64.b64decode(encoded)
        except Exception as e:
            raise ExtractionError(f"Failed to decode base64 image: {str(e)}")

        prompt = (
            "You are a piping engineering AI assistant. Analyze the uploaded piping isometric drawing (drawing image) "
            "and extract a structured Material Take-Off (MTO). "
            "Your output must be a single JSON object containing 'drawing_meta' and 'items'.\n\n"
            "CRITICAL RULES:\n"
            "1. Categories MUST be one of: ['PIPE', 'FITTING', 'FLANGE', 'VALVE', 'SUPPORT', 'WELD'].\n"
            "2. DO NOT extract GASKET or BOLT rows — these are programmatically derived later. Ignore them.\n"
            "3. For PIPE items, extract 'quantity' as the total length of the pipe run. Keep 'length_m' null or omit it.\n"
            "4. NPS Sizes must include double quotes (e.g. \"6\\\"\" or \"6\\\"x4\\\"\").\n"
            "5. Material specs should use ASME/ASTM vocabulary (e.g., 'ASTM A106 Gr.B', 'ASTM A234 WPB', 'ASTM A105', etc.).\n"
            "6. Read the title block for 'drawing_meta': drawing_no, revision, line_number, nps, material_class, service, design_pressure, design_temperature.\n"
            "7. Return ONLY valid JSON matching this schema:\n"
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
            "      \"confidence\": 0.9,\n"
            "      \"remarks\": \"string\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        # Prepare Gemini content parts
        contents = [
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        ]

        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.20,  # Low temp for deterministic extraction
        )

        # Attempt extraction with retries and exponential backoff
        attempts = 3
        for attempt in range(attempts):
            try:
                logger.info(f"Gemini API request attempt {attempt + 1}/{attempts}")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config
                )
                
                content = response.text
                if not content:
                    raise ExtractionError("Gemini returned an empty response.")
                
                # Parse output as JSON
                parsed_data = json.loads(content)
                
                # Check top-level keys
                if "drawing_meta" not in parsed_data or "items" not in parsed_data:
                    raise ValueError("JSON response missing required keys 'drawing_meta' or 'items'")
                
                return parsed_data
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Gemini extraction failed after {attempts} attempts: {str(e)}")
                    raise ExtractionError(f"Gemini extraction failed after {attempts} attempts: {str(e)}")
