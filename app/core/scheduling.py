from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def get_optimal_posting_time(platform: str, timezone: str) -> datetime:
    """
    MVP heuristic: pick the next hour in an "acceptable" window.
    This is intentionally simple and easy to replace later.
    """
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    if platform == "twitter":
        optimal_hours = [8, 9, 10, 12, 17, 18]
    else:
        optimal_hours = [10, 11, 15, 16]

    candidate = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    for _ in range(0, 72):  # look ahead max 3 days
        if candidate.hour in optimal_hours:
            return candidate
        candidate += timedelta(hours=1)
    return candidate

