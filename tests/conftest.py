"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.notify import reset_alerts
from src.ratelimit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    limiter.reset()
    reset_alerts()
    yield
    limiter.reset()
    reset_alerts()
