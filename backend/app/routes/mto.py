"""
MTO extraction routes.

Key architectural changes from the original synchronous version:

1. /api/upload (POST, 202 Accepted)
   - Validates content-type and file size inline (fast, sync).
   - Creates a PENDING job in the store immediately.
   - Schedules extraction as a FastAPI BackgroundTask (async, non-blocking).
   - Returns {job_id, status: PENDING} instantly — no HTTP timeout risk.

2. _run_extraction (background coroutine)
   - Offloads CPU-bound preprocessing (PIL / PyMuPDF) to a thread pool via
     asyncio.to_thread — event loop stays responsive.
   - Offloads blocking LLM HTTP calls to a thread pool the same way.
   - Falls back to MockExtractor if the primary extractor raises ExtractionError.
   - Updates the job to COMPLETED or FAILED when done.

3. /api/mto/{job_id} (GET)
   - Clients poll this to check status (PENDING → RUNNING → COMPLETED/FAILED).
   - Returns the full MTOResponse when ready.

4. /api/mto/{job_id}/csv (GET)
   - Streams a UTF-8 CSV of all MTO line items.

Rate limits:
   - /api/upload: 5 per minute per IP (protects LLM budget).
   - All other routes: 60 per minute (inherited from app default).
"""

import asyncio
import csv
import io
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.limiter import limiter
from app.schemas import ErrorResponse, JobStatus, MTOResponse, UploadResponse
import app.store as store
from app.services.extractor import ExtractionError, get_extractor
from app.services.preprocessor import PreprocessingError, preprocess_to_base64
from app.services.validator import validate_and_derive

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MTO Extraction"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _failed_response(job_id: str, source: str, message: str) -> MTOResponse:
    return MTOResponse(
        job_id=job_id,
        status=JobStatus.FAILED,
        source=source,          # type: ignore[arg-type]
        error_message=message,
        created_at=_utcnow(),
        completed_at=_utcnow(),
    )


# ---------------------------------------------------------------------------
# Background extraction task
# ---------------------------------------------------------------------------

async def _run_extraction(
    job_id: str,
    content: bytes,
    filename: str,
    settings: Settings,
) -> None:
    """
    Async background task: preprocess → extract → validate → store.
    Runs entirely outside the HTTP request-response cycle.
    """
    log = logging.LoggerAdapter(logger, extra={"job_id": job_id})
    extractor = get_extractor(settings)

    try:
        # Mark as RUNNING
        current = await store.get_job(job_id)
        if current:
            current.status = JobStatus.RUNNING
            await store.update_job(job_id, current)

        log.info(f"Extraction started (provider={extractor.source})")

        # --- CPU-bound: PDF render / PIL resize — thread pool ---
        t0 = time.time()
        try:
            image_b64, ocr_context = await asyncio.to_thread(
                preprocess_to_base64, content, filename
            )
            log.info(f"Preprocessing completed in {time.time() - t0:.2f} seconds")
        except PreprocessingError as e:
            raise ExtractionError(f"Preprocessing failed: {e}") from e

        # --- IO-bound: LLM API call — thread pool ---
        t1 = time.time()
        try:
            # 600-second hard ceiling for primary LLM extraction call (allows for multiple extractors in a chain to try and retry)
            raw_payload = await asyncio.wait_for(
                asyncio.to_thread(extractor.extract, image_b64, ocr_context),
                timeout=600.0,
            )
            log.info(f"Primary extractor ({extractor.source}) completed in {time.time() - t1:.2f} seconds")
        except (asyncio.TimeoutError, ExtractionError, Exception) as e:
            log.warning(
                f"Primary extractor ({extractor.source}) failed or timed out (falling back to mock) after {time.time() - t1:.2f} seconds: {e}",
                exc_info=True
            )
            from app.services.mock_extractor import MockExtractor
            extractor = MockExtractor()
            t2 = time.time()
            raw_payload = await asyncio.to_thread(extractor.extract, image_b64, ocr_context)
            log.info(f"Fallback mock extractor completed in {time.time() - t2:.2f} seconds")

        # --- Validate + derive ---
        mto_response = validate_and_derive(raw_payload, job_id)
        mto_response.source = extractor.source          # type: ignore[assignment]
        mto_response.image_b64 = image_b64
        mto_response.status = JobStatus.COMPLETED
        mto_response.completed_at = _utcnow()

        await store.update_job(job_id, mto_response)
        log.info(f"Extraction and validation completed successfully in {time.time() - t0:.2f} seconds")

    except Exception as exc:
        log.error(f"Extraction failed: {exc}", exc_info=True)
        failed = _failed_response(job_id, getattr(extractor, "source", "mock"), str(exc))
        await store.update_job(job_id, failed)


# ---------------------------------------------------------------------------
# POST /api/upload — fire-and-respond
# ---------------------------------------------------------------------------

@router.post(
    "/api/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadResponse,
    summary="Upload a drawing and start asynchronous MTO extraction",
    responses={
        202: {"description": "Job accepted — poll /api/mto/{job_id} for results"},
        400: {"model": ErrorResponse, "description": "Empty file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("5/minute")
async def upload_drawing(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    # --- Content-type guard ---
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PNG, JPEG, PDF.",
        )

    # --- File-size guard (read at most max+1 bytes) ---
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb} MB.",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # --- Create PENDING job immediately ---
    job_id = str(uuid.uuid4())
    pending = MTOResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        source="mock",           # placeholder; overwritten by extractor
        created_at=_utcnow(),
    )
    await store.create_job(job_id, pending)

    # --- Kick off extraction as a background task ---
    background_tasks.add_task(
        _run_extraction,
        job_id,
        content,
        file.filename or "upload",
        settings,
    )

    logger.info(
        f"Job {job_id} accepted (file={file.filename!r}, size={len(content)} bytes)"
    )
    return UploadResponse(job_id=job_id, status=JobStatus.PENDING)


# ---------------------------------------------------------------------------
# GET /api/mto/{job_id} — polling endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/api/mto/{job_id}",
    response_model=MTOResponse,
    summary="Retrieve MTO results (or current status) for a job",
    responses={
        200: {"description": "Job found — check status field for PENDING/RUNNING/COMPLETED/FAILED"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_mto(job_id: str) -> MTOResponse:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job


# ---------------------------------------------------------------------------
# GET /api/mto/{job_id}/csv — download completed MTO as CSV
# ---------------------------------------------------------------------------

@router.get(
    "/api/mto/{job_id}/csv",
    summary="Download MTO line items as CSV",
    responses={
        200: {"description": "UTF-8 CSV attachment"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        409: {"model": ErrorResponse, "description": "Job not yet completed"},
    },
)
async def get_mto_csv(job_id: str) -> StreamingResponse:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job '{job_id}' is not completed yet (status={job.status.value}).",
        )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "item_no", "category", "description", "size_nps",
        "schedule_rating", "material_spec", "end_type",
        "quantity", "unit", "length_m", "confidence", "remarks",
    ])

    for item in job.items:
        writer.writerow([
            item.item_no,
            item.category.value,
            item.description,
            item.size_nps,
            item.schedule_rating or "",
            item.material_spec or "",
            item.end_type or "",
            item.quantity,
            item.unit.value,
            item.length_m if item.length_m is not None else "",
            f"{item.confidence:.2f}" if item.confidence is not None else "",
            item.remarks or "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=mto_{job_id}.csv"},
    )
