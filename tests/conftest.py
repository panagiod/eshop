"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.ratelimit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    limiter.reset()
    yield
    limiter.reset()
