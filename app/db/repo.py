from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.config import Settings
from app.db.base import create_engine_and_sessionmaker, session_scope
from app.db.models import DistributionJob, PlatformPost
from app.schemas import Platform, ScriptCreateRequest
from app.observability.debug_log import write_debug_log


class Repo:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine, self.SessionLocal = create_engine_and_sessionmaker(settings.database_url)
        # Create tables (MVP convenience). Swap to Alembic later.
        from app.db.base import Base

        Base.metadata.create_all(self.engine)

    @classmethod
    def from_settings(cls, settings: Settings) -> "Repo":
        return cls(settings)

    def create_job(self, payload: ScriptCreateRequest) -> DistributionJob:
        job = DistributionJob(
            id=str(uuid.uuid4()),
            script_id=payload.script_id,
            script_title=payload.title,
            script_content=payload.content,
            status="pending",
            metadata_json=payload.metadata.model_dump_json(),
            preferences_json=payload.preferences.model_dump_json(),
        )
        # region agent log
        write_debug_log(
            location="app/db/repo.py:create_job",
            message="Creating distribution job",
            data={"job_id": job.id, "title": job.script_title},
            hypothesis_id="H4",
        )
        # endregion
        with session_scope(self.SessionLocal) as s:
            s.add(job)
        return job

    def get_job(self, job_id: str) -> DistributionJob | None:
        with session_scope(self.SessionLocal) as s:
            return s.get(DistributionJob, job_id)

    def set_job_status(self, job_id: str, status: str) -> None:
        with session_scope(self.SessionLocal) as s:
            job = s.get(DistributionJob, job_id)
            if not job:
                return
            job.status = status
            job.updated_at = datetime.utcnow()

    def list_posts(self, job_id: str) -> list[PlatformPost]:
        with session_scope(self.SessionLocal) as s:
            stmt = select(PlatformPost).where(PlatformPost.job_id == job_id).order_by(PlatformPost.created_at.asc())
            return list(s.execute(stmt).scalars().all())

    def upsert_generated_post(self, job_id: str, platform: Platform, content: dict[str, Any]) -> PlatformPost:
        with session_scope(self.SessionLocal) as s:
            stmt = select(PlatformPost).where(
                PlatformPost.job_id == job_id,
                PlatformPost.platform == platform.value,
            )
            existing = s.execute(stmt).scalars().first()
            if existing:
                existing.status = "generated"
                existing.content_json = json.dumps(content)
                existing.error_message = None
                existing.updated_at = datetime.utcnow()
                s.add(existing)
                return existing

            post = PlatformPost(
                id=str(uuid.uuid4()),
                job_id=job_id,
                platform=platform.value,
                status="generated",
                content_json=json.dumps(content),
            )
            s.add(post)
            return post

    def set_post_failure(self, post_id: str, message: str) -> None:
        with session_scope(self.SessionLocal) as s:
            post = s.get(PlatformPost, post_id)
            if not post:
                return
            post.status = "failed"
            post.error_message = message
            post.updated_at = datetime.utcnow()

    def mark_post_scheduled(
        self,
        post_id: str,
        scheduled_at: datetime | None,
        provider_post_id: str | None = None,
        provider_url: str | None = None,
        idempotency_key: str | None = None,
        raw_provider_response: dict[str, Any] | None = None,
    ) -> None:
        with session_scope(self.SessionLocal) as s:
            post = s.get(PlatformPost, post_id)
            if not post:
                return
            post.status = "scheduled" if scheduled_at else "published"
            post.scheduled_at = scheduled_at
            post.published_at = None if scheduled_at else datetime.utcnow()
            post.provider_post_id = provider_post_id
            post.provider_url = provider_url
            post.idempotency_key = idempotency_key
            # store raw response minimally in error_message? avoid; keep content_json pure.
            if raw_provider_response:
                # Attach response under content_json provider field (MVP convenience)
                try:
                    existing_content = json.loads(post.content_json) if post.content_json else {}
                except Exception:
                    existing_content = {}
                existing_content["_provider_response"] = raw_provider_response
                post.content_json = json.dumps(existing_content)
            post.error_message = None
            post.updated_at = datetime.utcnow()

    def find_post_by_idempotency(self, job_id: str, platform: Platform, idempotency_key: str) -> PlatformPost | None:
        with session_scope(self.SessionLocal) as s:
            stmt = select(PlatformPost).where(
                PlatformPost.job_id == job_id,
                PlatformPost.platform == platform.value,
                PlatformPost.idempotency_key == idempotency_key,
            )
            return s.execute(stmt).scalars().first()

    def get_preferences(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            return {}
        try:
            return json.loads(job.preferences_json)
        except Exception:
            return {}

    def get_metadata(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            return {}
        try:
            return json.loads(job.metadata_json)
        except Exception:
            return {}

