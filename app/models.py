from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="direct_url")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rq_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ServerState(Base):
    __tablename__ = "server_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    binary_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    host: Mapped[str | None] = mapped_column(String(200), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alias: Mapped[str | None] = mapped_column(String(200), nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ctx_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    threads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_gpu_layers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_args: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cmd: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="stopped")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
