import asyncio

from weixin_channel.constraints import RateLimiter


async def test_rate_limiter_allows_configured_rate() -> None:
    limiter = RateLimiter(max_calls=2, window_seconds=1)
    await asyncio.wait_for(limiter.acquire(), timeout=0.1)
    await asyncio.wait_for(limiter.acquire(), timeout=0.1)
