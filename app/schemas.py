from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Platform(str, Enum):
    twitter = "twitter"


class PostingTimeMode(str, Enum):
    optimal = "optimal"
    custom = "custom"


class ScriptMetadata(BaseModel):
    topic: str | None = None
    target_audience: str | None = None
    key_messages: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)


class CustomSchedule(BaseModel):
    twitter: datetime | None = None


class ScriptPreferences(BaseModel):
    include_images: bool = False
    posting_time: PostingTimeMode = PostingTimeMode.optimal
    timezone: str | None = None
    custom_schedule: CustomSchedule | None = None


class ScriptCreateRequest(BaseModel):
    title: str
    content: str
    script_id: str | None = None
    metadata: ScriptMetadata = Field(default_factory=ScriptMetadata)
    preferences: ScriptPreferences = Field(default_factory=ScriptPreferences)


JobStatus = Literal["pending", "processing", "completed", "failed"]
PlatformPostStatus = Literal["generated", "scheduled", "published", "failed", "skipped"]


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class PlatformPostResponse(BaseModel):
    id: str
    platform: Platform
    status: PlatformPostStatus
    content: dict[str, Any] | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    provider_post_id: str | None = None
    provider_url: str | None = None
    error_message: str | None = None


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    title: str
    script_id: str | None = None
    posts: list[PlatformPostResponse] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    job_id: str
    twitter: dict[str, Any] | None = None


class PublishRequest(BaseModel):
    publish: bool = True
    # If true and no generated content exists, generate it first.
    generate_if_missing: bool = True
    # Force re-generation even if generated content exists.
    regenerate: bool = False


class PublishResponse(BaseModel):
    job_id: str
    twitter: dict[str, Any] | None = None

