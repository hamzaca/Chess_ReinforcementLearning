"""Minimal tracing utility: timed spans logged to the console.

Swap for OpenTelemetry when distributed tracing is needed.
"""

import time
from contextlib import contextmanager
from typing import Iterator

from loguru import logger as console


@contextmanager
def trace(span_name: str) -> Iterator[None]:
    """Usage::

        with trace("agent.select_move"):
            move = agent.select_move(fen)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        console.debug("span={} duration_ms={:.1f}", span_name, elapsed_ms)
