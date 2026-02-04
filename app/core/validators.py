from __future__ import annotations

import re


class ContentValidator:
    TWITTER_TWEET_LIMIT = 280
    TWITTER_THREAD_MAX = 25
    LINKEDIN_POST_LIMIT = 3000
    LINKEDIN_HASHTAG_MAX = 30

    _ws_re = re.compile(r"[ \t]+\n")

    @classmethod
    def normalize(cls, text: str) -> str:
        text = text.replace("\r\n", "\n").strip()
        text = cls._ws_re.sub("\n", text)
        return text

    @classmethod
    def validate_twitter_thread(cls, tweets: list[str]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not tweets:
            errors.append("Thread is empty")
            return False, errors
        if len(tweets) > cls.TWITTER_THREAD_MAX:
            errors.append(f"Thread too long: {len(tweets)} tweets (max {cls.TWITTER_THREAD_MAX})")
        for i, t in enumerate(tweets):
            nt = cls.normalize(t)
            if len(nt) > cls.TWITTER_TWEET_LIMIT:
                errors.append(f"Tweet {i+1} exceeds 280 chars: {len(nt)}")
        return len(errors) == 0, errors

    @classmethod
    def validate_linkedin_post(cls, post: str, hashtags: list[str] | None = None) -> tuple[bool, list[str]]:
        errors: list[str] = []
        npost = cls.normalize(post)
        if not npost:
            errors.append("LinkedIn post is empty")
        if len(npost) > cls.LINKEDIN_POST_LIMIT:
            errors.append(f"Post exceeds {cls.LINKEDIN_POST_LIMIT} chars: {len(npost)}")
        if hashtags is not None and len(hashtags) > cls.LINKEDIN_HASHTAG_MAX:
            errors.append(f"Too many hashtags: {len(hashtags)} (max {cls.LINKEDIN_HASHTAG_MAX})")
        return len(errors) == 0, errors

