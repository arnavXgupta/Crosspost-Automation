from __future__ import annotations

import json
import logging
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for k, v in value.items():
            if k.lower() in {"authorization", "access_token", "api_key", "openai_api_key", "gemini_api_key"}:
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact(v)
        return redacted
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def json_log(logger: logging.Logger, message: str, **fields: Any) -> None:
    payload = {"msg": message, **redact(fields)}
    logger.info(json.dumps(payload, default=str))

