import logging
import logging.config
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.config import Settings, get_settings
from app.routes.mto import router as mto_router
import app.store as store

# ---------------------------------------------------------------------------
# Structured JSON logging — emits machine-readable log lines
# ---------------------------------------------------------------------------
LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "logging.Formatter",
            "fmt": '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s,"job_id":"%(job_id)s"}',
            "defaults": {"job_id": "-"},
        },
        "dev": {
            "format": "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "dev",   # swap to "json" in production
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

_START_TIME = time.time()


# ---------------------------------------------------------------------------
# Lifespan: initialize DB on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.init_db()
    logger.info("AutoMTO backend started")
    yield
    logger.info("AutoMTO backend shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AutoMTO API",
    description="Automatically extract structured Material Take-Offs from piping isometric drawings.",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "MTO Extraction",
            "description": "Upload isometric drawings and retrieve structured MTO data.",
        },
        {
            "name": "Liveness",
            "description": "Health and readiness probes for orchestration and monitoring.",
        },
    ],
)

# Wire rate-limiter into FastAPI exception handling
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(mto_router)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
from app.services.extractor import get_active_provider_name


@app.get(
    "/api/health",
    tags=["Liveness"],
    summary="Liveness + readiness check",
    responses={200: {"description": "Service is healthy"}},
)
async def health_check(
    request: Request,
    s: Settings = Depends(get_settings),
):
    total_jobs = await store.count_jobs()
    return {
        "status": "ok",
        "version": "0.1.0",
        "provider": get_active_provider_name(s),
        "uptime_s": round(time.time() - _START_TIME, 1),
        "jobs_total": total_jobs,
    }
