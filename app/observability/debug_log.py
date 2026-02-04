from __future__ import annotations

import json
import time
from typing import Any


LOG_PATH = r"c:\Users\arnav\OneDrive\Desktop\social-media-pipeline\.cursor\debug.log"


def write_debug_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    run_id: str = "run1",
    hypothesis_id: str = "H?",
) -> None:
    """Append a single NDJSON debug log line. Keep it tiny and cheap."""
    payload = {
        "sessionId": "debug-session",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        # Debug logging must never break the app
        pass

