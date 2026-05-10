"""Realtime event broker abstraction.

The broker decouples *where* an event is produced from *which* connected
sockets receive it. The default :class:`InMemoryBroker` simply asks the
local :class:`ConnectionManager` to fan out — sufficient for a single API
process. The :class:`RedisBroker` publishes events to a Redis channel and
subscribes to receive events from peer API processes, so a horizontally
scaled deployment behaves as if all sockets shared one event bus.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Protocol
from uuid import UUID

from app.realtime.manager import ConnectionManager

logger = logging.getLogger(__name__)


class RealtimeBroker(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def publish(
        self,
        map_id: UUID,
        envelope: dict[str, Any],
        *,
        skip_client_id: str | None = None,
    ) -> None: ...


class InMemoryBroker:
    """Single-process broker that fans out via the local manager directly."""

    def __init__(self, manager: ConnectionManager) -> None:
        self.manager = manager

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def publish(
        self,
        map_id: UUID,
        envelope: dict[str, Any],
        *,
        skip_client_id: str | None = None,
    ) -> None:
        await self.manager.local_fanout(
            map_id, envelope, skip_client_id=skip_client_id
        )


class RedisBroker:
    """Redis pub/sub broker for multi-process deployments.

    All envelopes are published to a single channel ``dndmap:events``. Each
    process subscribes once on startup; a background task reads messages and
    delegates to the local manager for the targeted map. A
    ``skip_client_id`` is encoded into the wire message so the original
    producer's local fanout can suppress echoes — peer processes that did
    not originate the event always fan out to all of their connections.
    """

    CHANNEL = "dndmap:events"

    def __init__(self, redis_url: str, manager: ConnectionManager) -> None:
        self.redis_url = redis_url
        self.manager = manager
        self._publisher = None  # type: ignore[var-annotated]
        self._subscriber = None  # type: ignore[var-annotated]
        self._task: asyncio.Task[None] | None = None
        self._instance_id = __import__("uuid").uuid4().hex

    async def start(self) -> None:
        try:
            from redis.asyncio import Redis  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - guarded by config
            raise RuntimeError(
                "redis package not installed; install with 'pip install redis'"
            ) from exc

        self._publisher = Redis.from_url(self.redis_url, decode_responses=True)
        self._subscriber = Redis.from_url(self.redis_url, decode_responses=True)
        pubsub = self._subscriber.pubsub()
        await pubsub.subscribe(self.CHANNEL)
        self._task = asyncio.create_task(self._reader_loop(pubsub))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._publisher is not None:
            await self._publisher.aclose()
            self._publisher = None
        if self._subscriber is not None:
            await self._subscriber.aclose()
            self._subscriber = None

    async def publish(
        self,
        map_id: UUID,
        envelope: dict[str, Any],
        *,
        skip_client_id: str | None = None,
    ) -> None:
        if self._publisher is None:
            return
        message = {
            "origin": self._instance_id,
            "map_id": str(map_id),
            "skip_client_id": skip_client_id,
            "envelope": envelope,
        }
        await self._publisher.publish(self.CHANNEL, json.dumps(message))

    async def _reader_loop(self, pubsub: Any) -> None:
        async for raw in pubsub.listen():
            if raw is None or raw.get("type") != "message":
                continue
            try:
                message = json.loads(raw["data"])
                map_id = UUID(message["map_id"])
                envelope = message["envelope"]
                # If this process originated the event, suppress the
                # specified socket so the actor doesn't see their own echo;
                # otherwise fan out to all local sockets.
                skip = (
                    message.get("skip_client_id")
                    if message.get("origin") == self._instance_id
                    else None
                )
                await self.manager.local_fanout(
                    map_id, envelope, skip_client_id=skip
                )
            except Exception:  # pragma: no cover - defensive
                logger.exception("Failed to dispatch realtime event from Redis")


def build_broker(
    redis_url: str | None, manager: ConnectionManager
) -> RealtimeBroker:
    if redis_url:
        return RedisBroker(redis_url, manager)
    return InMemoryBroker(manager)
