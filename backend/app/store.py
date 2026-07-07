"""
Persistent async job store backed by SQLite (aiosqlite).

Public interface (mirrors the old in-memory store):
  - init_db()               → called once on startup to create the table
  - create_job(job_id, job) → insert a new job row
  - get_job(job_id)         → fetch and deserialize a single job
  - update_job(job_id, job) → overwrite an existing job row
  - count_jobs()            → return total number of stored jobs

All functions are async-safe; no threading locks needed.
The DB file (jobs.db) is created in the backend working directory.
"""

import aiosqlite
import logging
from typing import Optional
from app.schemas import MTOResponse

logger = logging.getLogger(__name__)

DB_PATH = "jobs.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id   TEXT PRIMARY KEY,
    status   TEXT NOT NULL,
    data     TEXT NOT NULL,           -- Full MTOResponse as JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Indexes for common query patterns
_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""


async def init_db() -> None:
    """Initialize the SQLite database and create the jobs table if absent."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLE_SQL)
        await db.execute(_CREATE_INDEX_SQL)
        await db.commit()
    logger.info(f"Job store initialized at '{DB_PATH}'")


async def create_job(job_id: str, job: MTOResponse) -> None:
    """Insert a new job into the store. Raises if job_id already exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jobs (job_id, status, data) VALUES (?, ?, ?)",
            (job_id, job.status.value, job.model_dump_json()),
        )
        await db.commit()
    logger.debug("Job created", extra={"job_id": job_id})


async def get_job(job_id: str) -> Optional[MTOResponse]:
    """Fetch a job by ID. Returns None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT data FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return MTOResponse.model_validate_json(row[0])


async def update_job(job_id: str, job: MTOResponse) -> None:
    """Overwrite the data and status for an existing job."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET data = ?, status = ? WHERE job_id = ?",
            (job.model_dump_json(), job.status.value, job_id),
        )
        await db.commit()
    logger.debug("Job updated", extra={"job_id": job_id, "status": job.status.value})


async def count_jobs() -> int:
    """Return the total number of jobs in the store."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM jobs") as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0
