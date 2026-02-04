from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.validators import ContentValidator
from app.observability.debug_log import write_debug_log

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedContent:
    twitter: dict[str, Any]


class AIContentGenerator:
    def __init__(self, api_key: str | None, model: str):
        self.api_key = api_key
        self.model = model

    def _client(self):
        # region agent log
        write_debug_log(
            location="app/core/ai.py:_client",
            message="Creating Gemini client",
            data={"has_api_key": bool(self.api_key), "model": self.model},
            hypothesis_id="H1",
        )
        # endregion
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(self.model)

    def generate(self, script: str, metadata: dict[str, Any] | None = None, research: str = "") -> GeneratedContent:
        metadata = metadata or {}
        script = ContentValidator.normalize(script)

        model = self._client()

        twitter_prompt = self._twitter_prompt(script=script, metadata=metadata, research=research)

        twitter_obj = self._json_completion(model, twitter_prompt, schema_name="TwitterThread")

        # Normalize and validate (Twitter only for this project)
        tweets = [ContentValidator.normalize(t) for t in twitter_obj.get("tweets", []) if isinstance(t, str)]
        ok, errors = ContentValidator.validate_twitter_thread(tweets)
        if not ok:
            raise ValueError(f"Twitter validation failed: {errors}")

        twitter = {"tweets": tweets}
        return GeneratedContent(twitter=twitter)

    def _json_completion(self, model, prompt: str, schema_name: str) -> dict[str, Any]:
        """
        Uses Gemini's structured output capability.
        """
        try:
            # Note: For Gemini 1.5, we can use response_mime_type="application/json"
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            text = response.text
        except Exception as e:
            logger.exception("Failed to get response from Gemini: %s", e)
            raise RuntimeError(f"Gemini API call failed for {schema_name}")

        try:
            obj = json.loads(text)
        except Exception as e:
            logger.exception("Failed to parse %s JSON from Gemini: %s", schema_name, e)
            raise ValueError(f"Gemini did not return valid JSON for {schema_name}")
        
        if not isinstance(obj, dict):
            raise ValueError(f"Gemini returned non-object JSON for {schema_name}")
        return obj

    def _twitter_prompt(self, script: str, metadata: dict[str, Any], research: str) -> str:
        topic = metadata.get("topic") or ""
        return f"""
You are a social media expert specializing in Twitter/X engagement.

Convert the following Instagram reel script into a compelling Twitter thread.

Requirements:
- Create 3-7 tweets forming a cohesive thread
- First tweet: hook under 280 characters
- Middle tweets: value-packed insights, each under 280 characters
- Final tweet: CTA or thought-provoking question
- Use line breaks for readability
- Include 2-3 relevant hashtags ONLY in the final tweet
- Conversational tone

Topic: {topic}
Research context (optional): {research}

Script:
{script}

Return ONLY valid JSON in this shape:
{{"tweets": ["tweet1", "tweet2", "tweet3"]}}
""".strip()

class ResearchProvider:
    def get_context(self, metadata: dict[str, Any], script: str) -> str:
        raise NotImplementedError


class NoResearchProvider(ResearchProvider):
    def get_context(self, metadata: dict[str, Any], script: str) -> str:
        return ""

