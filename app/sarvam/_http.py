"""Shared retry wrapper for Sarvam REST calls. A live call hit a transient
`httpx.ReadError` on a TTS request mid-conversation - the caller heard
nothing back for that turn because the request wasn't retried. Network
blips are expected over a real connection; one retry with a short backoff
costs little and avoids a silently dropped turn.
"""
from __future__ import annotations

import asyncio
import typing

import httpx

T = typing.TypeVar("T")


async def with_retry(call: typing.Callable[[], typing.Awaitable[T]], attempts: int = 2) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await call()
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < attempts - 1:
                await asyncio.sleep(0.3)
    raise last_exc
