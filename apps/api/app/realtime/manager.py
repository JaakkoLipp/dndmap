"""Per-process WebSocket connection registry and fanout.

The :class:`ConnectionManager` is the in-process source of truth for which
sockets are connected to which map, and is responsible for sending JSON
envelopes to each socket. A :class:`RealtimeBroker` calls
:meth:`ConnectionManager.local_fanout` to deliver events to local sockets;
for single-process deployments the broker just calls this directly, for
multi-process deployments the Redis broker fans out after subscribing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.domain.models import utc_now
from app.realtime.events import Actor


@dataclass(eq=False)
class ConnectionInfo:
    """Metadata for a single connected WebSocket.

    Equality and hash are identity-based so two distinct sockets compare
    different even when they belong to the same user/client_id.
    """

    websocket: WebSocket
    client_id: str
    actor: Actor | None
    joined_at: datetime = field(default_factory=utc_now)

    def __hash__(self) -> int:  # pragma: no cover - trivial
        return id(self)


class ConnectionManager:
    """Tracks connected sockets per map and fans events out locally."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[ConnectionInfo]] = {}
        self._lock = asyncio.Lock()

    async def register(self, map_id: UUID, info: ConnectionInfo) -> None:
        async with self._lock:
            self._connections.setdefault(map_id, set()).add(info)

    async def unregister(self, map_id: UUID, info: ConnectionInfo) -> None:
        async with self._lock:
            conns = self._connections.get(map_id)
            if conns is None:
                return
            conns.discard(info)
            if not conns:
                self._connections.pop(map_id, None)

    def snapshot(self, map_id: UUID) -> list[dict[str, Any]]:
        """Return a list of presence entries for everyone connected locally."""
        conns = self._connections.get(map_id, set())
        return [
            {
                "client_id": info.client_id,
                "actor": info.actor,
                "joined_at": info.joined_at.isoformat(),
            }
            for info in conns
        ]

    async def send_to(self, info: ConnectionInfo, envelope: dict[str, Any]) -> None:
        try:
            await info.websocket.send_json(envelope)
        except Exception:
            # Socket died mid-send; drop it. The receive loop will surface the
            # disconnect and call unregister().
            pass

    async def local_fanout(
        self,
        map_id: UUID,
        envelope: dict[str, Any],
        *,
        skip_client_id: str | None = None,
    ) -> None:
        """Send an envelope to all locally connected sockets for ``map_id``.

        ``skip_client_id`` lets a publisher exclude the originating socket so
        an actor does not receive an echo of their own action.
        """
        targets: list[ConnectionInfo]
        async with self._lock:
            conns = self._connections.get(map_id, set())
            targets = [c for c in conns if c.client_id != skip_client_id]
        if not targets:
            return
        await asyncio.gather(
            *(self.send_to(info, envelope) for info in targets),
            return_exceptions=True,
        )
