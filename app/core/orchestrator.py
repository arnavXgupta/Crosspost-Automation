from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.config import Settings
from app.core.ai import AIContentGenerator, NoResearchProvider
from app.core.scheduling import get_optimal_posting_time
from app.db.repo import Repo
from app.schemas import Platform, PublishRequest
from app.observability.debug_log import write_debug_log

logger = logging.getLogger(__name__)


@dataclass
class Orchestrator:
    settings: Settings
    repo: Repo

    @classmethod
    def from_settings(cls, settings: Settings, repo: Repo) -> "Orchestrator":
        return cls(settings=settings, repo=repo)

    def generate_preview(self, job_id: str) -> dict[str, Any]:
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError("Job not found")

        # region agent log
        write_debug_log(
            location="app/core/orchestrator.py:generate_preview",
            message="Entered generate_preview",
            data={"job_id": job_id},
            hypothesis_id="H1",
        )
        # endregion

        self.repo.set_job_status(job_id, "processing")
        try:
            metadata = self.repo.get_metadata(job_id)
            # preferences may be used later for more nuanced generation; kept for symmetry
            self.repo.get_preferences(job_id)

            research = NoResearchProvider().get_context(metadata=metadata, script=job.script_content)
            generator = AIContentGenerator(api_key=self.settings.gemini_api_key, model=self.settings.gemini_model)
            generated = generator.generate(script=job.script_content, metadata=metadata, research=research)

            tw_post = self.repo.upsert_generated_post(job_id, Platform.twitter, generated.twitter)

            self.repo.set_job_status(job_id, "completed")
            # region agent log
            write_debug_log(
                location="app/core/orchestrator.py:generate_preview",
                message="Generated preview",
                data={"job_id": job_id, "has_twitter": bool(tw_post.content_json)},
                hypothesis_id="H2",
            )
            # endregion
            return {"twitter": json.loads(tw_post.content_json or "{}")}
        except Exception as e:
            logger.exception("Preview generation failed: %s", e)
            self.repo.set_job_status(job_id, "failed")
            raise

    def _resolve_schedule_time(self, platform: Platform, preferences: dict[str, Any]) -> datetime | None:
        mode = preferences.get("posting_time", "optimal")
        timezone = preferences.get("timezone") or self.settings.default_timezone
        if mode == "custom":
            custom = preferences.get("custom_schedule") or {}
            raw = custom.get(platform.value)
            if raw:
                if isinstance(raw, str):
                    # Accept ISO strings
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if isinstance(raw, datetime):
                    return raw
        return get_optimal_posting_time(platform.value, timezone=timezone)

    def publish(self, job_id: str, req: PublishRequest, idempotency_key: str | None) -> dict[str, Any]:
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError("Job not found")

        # region agent log
        write_debug_log(
            location="app/core/orchestrator.py:publish",
            message="Entered publish",
            data={"job_id": job_id, "regenerate": req.regenerate, "generate_if_missing": req.generate_if_missing},
            hypothesis_id="H3",
        )
        # endregion

        # Ensure generated content exists (Twitter only)
        posts = {p.platform: p for p in self.repo.list_posts(job_id)}
        if req.regenerate or (req.generate_if_missing and "twitter" not in posts):
            self.generate_preview(job_id=job_id)
            posts = {p.platform: p for p in self.repo.list_posts(job_id)}

        from app.integrations.twitter_composio import TwitterPublisher
        from app.utils.retry import retry

        preferences = self.repo.get_preferences(job_id)

        results: dict[str, Any] = {}

        # Twitter
        tw_post = posts.get("twitter")
        if tw_post:
            if idempotency_key:
                existing = self.repo.find_post_by_idempotency(job_id, Platform.twitter, idempotency_key)
                if existing and existing.provider_post_id:
                    results["twitter"] = json.loads(existing.content_json or "{}")
                else:
                    results["twitter"] = self._publish_twitter(tw_post, preferences, idempotency_key, retry, TwitterPublisher)
            else:
                results["twitter"] = self._publish_twitter(tw_post, preferences, None, retry, TwitterPublisher)

        return results

    def _publish_twitter(self, post, preferences, idempotency_key, retry_fn, PublisherCls):
        try:
            content = json.loads(post.content_json or "{}")
            tweets = content.get("tweets", [])
            publisher = PublisherCls.from_settings(self.settings)
            scheduled_at = self._resolve_schedule_time(Platform.twitter, preferences)

            resp = retry_fn(lambda: publisher.publish_thread(tweets=tweets, scheduled_at=scheduled_at))
            self.repo.mark_post_scheduled(
                post_id=post.id,
                scheduled_at=scheduled_at,
                provider_post_id=resp.get("thread_id") or resp.get("id"),
                provider_url=resp.get("url"),
                idempotency_key=idempotency_key,
                raw_provider_response=resp,
            )
            return resp
        except Exception as e:
            self.repo.set_post_failure(post.id, str(e))
            raise

