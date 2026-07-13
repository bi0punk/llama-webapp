from __future__ import annotations

from app.db import session_scope
from app.models import Job


def get_jobs(limit: int = 50) -> list[Job]:
    with session_scope() as s:
        return s.query(Job).order_by(Job.created_at.desc()).limit(limit).all()


def create_job(
    type_: str,
    status: str = "queued",
    progress: int = 0,
    message: str | None = None,
    rq_job_id: str | None = None,
) -> Job:
    with session_scope() as s:
        job = Job(
            type=type_,
            status=status,
            progress=progress,
            message=message,
            rq_job_id=rq_job_id,
        )
        s.add(job)
        s.flush()
        created = s.get(Job, job.id)
        assert created is not None
        return created


def update_job(job_id: int, **kwargs: str | int | None) -> None:
    with session_scope() as s:
        job = s.get(Job, job_id)
        if job:
            for key, value in kwargs.items():
                setattr(job, key, value)
