from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry(fn: Callable[[], T], attempts: int = 3, base_delay_s: float = 0.5) -> T:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # MVP: keep broad, tighten later.
            last_exc = e
            if i == attempts - 1:
                break
            time.sleep(base_delay_s * (2**i))
    assert last_exc is not None
    raise last_exc

