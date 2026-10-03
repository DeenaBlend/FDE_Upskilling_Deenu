# tests/test_rate_limit_strategy.py
"""Unit tests for rate limiting strategies.

Unlike test_patterns.test_rate_limiting, these don't depend on wall-clock timing:
concurrency is counted directly and asyncio.sleep is mocked for the token bucket.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.strategies.rate_limit_strategy import (
    RateLimitStrategy,
    SemaphoreStrategy,
    TokenBucketStrategy,
)

SLEEP = "src.strategies.rate_limit_strategy.asyncio.sleep"


def test_strategy_is_abstract():
    with pytest.raises(TypeError):
        RateLimitStrategy()


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    strategy = SemaphoreStrategy(max_concurrent=2)
    in_flight = 0
    peak = 0

    async def task():
        nonlocal in_flight, peak
        await strategy.acquire()
        try:
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
        finally:
            in_flight -= 1
            strategy.release()

    await asyncio.gather(*(task() for _ in range(6)))

    assert peak == 2


@pytest.mark.asyncio
async def test_semaphore_blocks_until_released():
    strategy = SemaphoreStrategy(max_concurrent=1)
    await strategy.acquire()

    waiter = asyncio.create_task(strategy.acquire())
    await asyncio.sleep(0)
    assert not waiter.done()

    strategy.release()
    await asyncio.wait_for(waiter, timeout=1)
    strategy.release()


@pytest.mark.asyncio
async def test_token_bucket_allows_burst_up_to_rate():
    bucket = TokenBucketStrategy(rate=3, per=1.0)

    with patch(SLEEP, new_callable=AsyncMock) as sleep:
        for _ in range(3):
            await bucket.acquire()

    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_token_bucket_sleeps_when_tokens_run_out():
    bucket = TokenBucketStrategy(rate=2, per=1.0)

    with patch(SLEEP, new_callable=AsyncMock) as sleep:
        for _ in range(3):
            await bucket.acquire()

    sleep.assert_awaited_once()
    wait = sleep.await_args.args[0]
    assert 0 < wait <= 0.5  # at most one token's worth: per / rate
    assert bucket.allowance == 0.0


@pytest.mark.asyncio
async def test_token_bucket_refills_but_never_exceeds_rate():
    bucket = TokenBucketStrategy(rate=5, per=1.0)
    bucket.allowance = 0.0
    bucket.last_check = datetime.now() - timedelta(seconds=60)

    with patch(SLEEP, new_callable=AsyncMock) as sleep:
        await bucket.acquire()

    sleep.assert_not_awaited()
    assert bucket.allowance == 4.0  # capped at rate (5), minus the token just used


def test_token_bucket_release_is_noop():
    bucket = TokenBucketStrategy(rate=1, per=1.0)
    bucket.release()
    assert bucket.allowance == 1
