import asyncio
import base64
import os
import logging
import json
from app.config import get_settings
from app.services.extractor import get_extractor
from app.services.preprocessor import preprocess_to_base64
from app.services.validator import validate_and_derive

# Configure logging for the script execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_images")

async def process_image(filepath, job_id):
    settings = get_settings()
    extractor = get_extractor(settings)
    
    filename = os.path.basename(filepath)
    print(f"\n--- Processing {filename} with {extractor.source} ---", flush=True)
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.", flush=True)
        return None
        
    print(f"Reading file: {filepath}...", flush=True)
    with open(filepath, "rb") as f:
        content = f.read()
    
    try:
        # Preprocess
        print(f"Step 1: Preprocessing image/PDF...", flush=True)
        image_b64, ocr_context = await asyncio.to_thread(preprocess_to_base64, content, filename)
        print(f"Preprocessing complete. Base64 payload size: {len(image_b64)} characters.", flush=True)
        
        # Extract
        print(f"Step 2: Sending request to extraction provider ({extractor.source})...", flush=True)
        print("Note: Vision extraction can take 10-60+ seconds depending on API response time.", flush=True)
        start_time = asyncio.get_event_loop().time()
        raw_payload = await asyncio.to_thread(extractor.extract, image_b64, ocr_context)
        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"Extraction successful! Completed in {elapsed:.2f} seconds.", flush=True)
        
        # Validate
        print(f"Step 3: Validating schema and deriving components...", flush=True)
        mto_response = validate_and_derive(raw_payload, job_id)
        print(f"Validation successful.", flush=True)
        
        # Output
        print("\n=== EXTRACTION RESULTS ===")
        print(f"Metadata: {mto_response.drawing_meta}")
        print("Items:")
        for item in mto_response.items:
            print(f"  {item.item_no}: {item.quantity} {item.unit.value} {item.category.value} | {item.size_nps} | {item.description} | {item.material_spec} | Remarks: {item.remarks}")
        print(f"Summary: {mto_response.summary}")
        print("==========================\n")
        
        return mto_response
    except Exception as e:
        print(f"Error processing {filename}: {e}", flush=True)

async def main():
    await process_image("../assets/tests/test1.png", "job_1")
    await process_image("../assets/tests/test2.png", "job_2")

if __name__ == "__main__":
    asyncio.run(main())
