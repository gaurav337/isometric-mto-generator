import base64
import io
from PIL import Image
import fitz  # PyMuPDF

class PreprocessingError(Exception):
    pass

def preprocess_to_base64(file_bytes: bytes, original_filename: str = "") -> str:
    """
    Preprocess drawing files (JPEG, PNG, PDF):
    - Decides PDF vs Image based on magic bytes.
    - PDF: Renders first page at 150 DPI.
    - Image: Normalizes format, scales if size > 2048px.
    - Converts to RGB.
    - Returns base64 encoded JPEG data URL string.
    """
    if not file_bytes:
        raise PreprocessingError("File content is empty.")

    # Detect file type using magic bytes
    # %PDF = b'%PDF'
    # PNG = b'\x89PNG\r\n\x1a\n'
    # JPEG = b'\xff\xd8\xff'
    is_pdf = file_bytes.startswith(b'%PDF')
    
    img = None
    try:
        if is_pdf:
            # Render first page of PDF using PyMuPDF (fitz)
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) == 0:
                raise PreprocessingError("PDF has no pages.")
            page = doc[0]
            # Render at 150 DPI (matrix zoom = 150 / 72 = 2.0833)
            zoom = 2.0833
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert fitz pixmap to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            doc.close()
        else:
            # Try loading as normal image
            img = Image.open(io.BytesIO(file_bytes))
    except Exception as e:
        raise PreprocessingError(f"Failed to open/render file: {str(e)}")

    if img is None:
        raise PreprocessingError("Could not decode file content as image or PDF.")

    try:
        # Convert to RGB if needed (handling RGBA or grayscale)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if image exceeds maximum resolution of 2048px on either dimension
        max_dim = 2048
        width, height = img.size
        if width > max_dim or height > max_dim:
            if width > height:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            else:
                new_height = max_dim
                new_width = int(width * (max_dim / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save to memory as JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        jpeg_bytes = buffer.getvalue()
        
        # Encode to base64
        base64_str = base64.b64encode(jpeg_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_str}"
    except Exception as e:
        raise PreprocessingError(f"Failed to process image: {str(e)}")
