from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.config import Settings
from app.observability.debug_log import write_debug_log

logger = logging.getLogger(__name__)


@dataclass
class TwitterPublisher:
    api_key: str
    user_id: str = "default"

    @classmethod
    def from_settings(cls, settings: Settings) -> "TwitterPublisher":
        if not settings.composio_api_key:
            raise RuntimeError("COMPOSIO_API_KEY is not set")
        return cls(
            api_key=settings.composio_api_key,
            user_id=settings.composio_user_id,
        )

    def _get_client(self):
        """
        Get the Composio client with the configured API key.
        SDK v0.7.x uses Composio class with actions.execute().
        """
        try:
            from composio import Composio
        except ImportError as e:
            raise RuntimeError(
                "Composio SDK not installed. Add 'composio' to requirements."
            ) from e

        return Composio(api_key=self.api_key)

    def publish_thread(self, tweets: list[str], scheduled_at: datetime | None) -> dict[str, Any]:
        # region agent log
        write_debug_log(
            location="app/integrations/twitter_composio.py:publish_thread",
            message="Publishing thread via Composio",
            data={"tweet_count": len(tweets), "has_schedule": bool(scheduled_at)},
            hypothesis_id="H5",
        )
        # endregion
        
        client = self._get_client()
        
        # Import Action class for creating action objects from slug strings
        from composio import Action

        # Get the connected Twitter account for this entity
        # The SDK requires the connected_account ID for apps requiring authentication
        connected_accounts = client.connected_accounts.get()
        twitter_account = next(
            (ca for ca in connected_accounts if ca.appName == "twitter" and ca.entityId == self.user_id),
            None
        )
        if not twitter_account:
            raise RuntimeError(
                f"No Twitter account connected for entity '{self.user_id}'. "
                "Please connect your Twitter account in Composio dashboard."
            )
        connected_account_id = twitter_account.id

        # For a thread, we post each tweet in sequence, replying to the previous one
        tweet_ids: list[str] = []
        first_tweet_url: str | None = None
        
        for i, tweet_text in enumerate(tweets):
            params: dict[str, Any] = {"text": tweet_text}
            
            # If this is not the first tweet, reply to the previous tweet
            if tweet_ids:
                params["reply"] = {"in_reply_to_tweet_id": tweet_ids[-1]}
            
            # Execute the Twitter post action using SDK v0.7.x API
            # actions.execute(action, params, entity_id, connected_account)
            action = Action("TWITTER_CREATION_OF_A_POST")
            result = client.actions.execute(
                action=action,
                params=params,
                entity_id=self.user_id,
                connected_account=connected_account_id
            )
            
            # Handle the response - check if it's a dict or has data attribute
            result_data = result if isinstance(result, dict) else getattr(result, "data", result)
            if isinstance(result_data, dict):
                tweet_id = result_data.get("data", {}).get("id") or result_data.get("id")
                if tweet_id:
                    tweet_ids.append(tweet_id)
                if i == 0 and not first_tweet_url:
                    # Construct URL from first tweet
                    first_tweet_url = result_data.get("url") or (
                        f"https://twitter.com/i/status/{tweet_id}" if tweet_id else None
                    )
        
        return {
            "success": True,
            "thread_id": tweet_ids[0] if tweet_ids else None,
            "tweet_ids": tweet_ids,
            "url": first_tweet_url,
            "raw": {"tweets_posted": len(tweet_ids)},
        }

    @staticmethod
    def _normalize(out: Any) -> dict[str, Any]:
        if isinstance(out, dict):
            return {
                "success": True,
                "thread_id": out.get("id") or out.get("thread_id"),
                "tweet_ids": out.get("tweet_ids") or out.get("tweets") or out.get("ids"),
                "url": out.get("url"),
                "raw": out,
            }
        return {"success": True, "raw": out}

