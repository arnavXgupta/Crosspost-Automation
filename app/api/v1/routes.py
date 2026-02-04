from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Query

from app.config import Settings, get_settings
from app.core.orchestrator import Orchestrator
from app.db.repo import Repo
from app.schemas import (
    JobCreateResponse,
    JobResponse,
    Platform,
    PreviewResponse,
    PublishRequest,
    PublishResponse,
    ScriptCreateRequest,
)
import json

router = APIRouter(prefix="/api/v1", tags=["v1"])


def _auth(settings: Settings, authorization: str | None) -> None:
    if not settings.api_auth_token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.api_auth_token:
        raise HTTPException(status_code=403, detail="Invalid token")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/scripts", response_model=JobCreateResponse)
def create_script_job(
    payload: ScriptCreateRequest,
    background: BackgroundTasks,
    sync: bool = Query(default=False, description="Run processing synchronously (dev only)"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> JobCreateResponse:
    _auth(settings, authorization)

    repo = Repo.from_settings(settings)
    orchestrator = Orchestrator.from_settings(settings, repo=repo)
    job = repo.create_job(payload)

    if sync:
        orchestrator.generate_preview(job_id=job.id)
    else:
        background.add_task(orchestrator.generate_preview, job_id=job.id)

    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> JobResponse:
    _auth(settings, authorization)
    repo = Repo.from_settings(settings)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    posts = repo.list_posts(job_id)
    return JobResponse(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        title=job.script_title,
        script_id=job.script_id,
        posts=[
            {
                "id": p.id,
                "platform": Platform(p.platform),
                "status": p.status,
                "content": (
                    json.loads(p.content_json)
                    if isinstance(p.content_json, str)
                    else p.content_json
                ),
                "scheduled_at": p.scheduled_at,
                "published_at": p.published_at,
                "provider_post_id": p.provider_post_id,
                "provider_url": p.provider_url,
                "error_message": p.error_message,
            }
            for p in posts
        ],
    )


@router.post("/jobs/{job_id}/preview", response_model=PreviewResponse)
def preview_job(
    job_id: str,
    background: BackgroundTasks,
    sync: bool = Query(default=False, description="Run synchronously (dev only)"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> PreviewResponse:
    _auth(settings, authorization)
    repo = Repo.from_settings(settings)
    if not repo.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    orchestrator = Orchestrator.from_settings(settings, repo=repo)
    if sync:
        result = orchestrator.generate_preview(job_id=job_id)
        return PreviewResponse(job_id=job_id, twitter=result.get("twitter"))
    background.add_task(orchestrator.generate_preview, job_id=job_id)
    return PreviewResponse(job_id=job_id)


@router.post("/jobs/{job_id}/publish", response_model=PublishResponse)
def publish_job(
    job_id: str,
    background: BackgroundTasks,
    req: PublishRequest = Body(default_factory=PublishRequest),
    sync: bool = Query(default=False, description="Run synchronously (dev only)"),
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    settings: Settings = Depends(get_settings),
) -> PublishResponse:
    _auth(settings, authorization)
    repo = Repo.from_settings(settings)
    if not repo.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    orchestrator = Orchestrator.from_settings(settings, repo=repo)

    if sync:
        result = orchestrator.publish(job_id=job_id, req=req, idempotency_key=idempotency_key)
        return PublishResponse(job_id=job_id, twitter=result.get("twitter"))

    background.add_task(orchestrator.publish, job_id=job_id, req=req, idempotency_key=idempotency_key)
    return PublishResponse(job_id=job_id)

