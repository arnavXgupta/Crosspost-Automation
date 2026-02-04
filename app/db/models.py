from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class DistributionJob(Base):
    __tablename__ = "distribution_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    script_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    script_title: Mapped[str] = mapped_column(String(500), nullable=False)
    script_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    preferences_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    posts: Mapped[list["PlatformPost"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class PlatformPost(Base):
    __tablename__ = "platform_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("distribution_jobs.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # twitter|linkedin
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generated")

    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    provider_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    job: Mapped[DistributionJob] = relationship(back_populates="posts")

