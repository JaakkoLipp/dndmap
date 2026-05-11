"""WebSocket endpoint for map collaboration.

Authenticated when ``AUTH_ENABLED=true``: the access_token cookie is decoded
and campaign membership is checked. The endpoint sends a presence snapshot
on connect, broadcasts ``presence.joined``/``presence.left`` events, and
echoes client-sent messages through the realtime broker so they reach every
process subscribed to the same map.

The wire envelope is the standard shape produced by
``app.realtime.events.build_envelope``.

Lock messages
-------------
Clients send ``{"type": "lock.acquire", "object_id": "..."}`` (and
``"lock.release"`` / ``"lock.refresh"``) to coordinate object editing. The
server is the source of truth: the lock store is consulted, and the
outcome is broadcast as ``lock.acquired`` / ``lock.released`` or sent
back to the requesting socket only as ``lock.denied``. Locks have a TTL
so an abandoned edit clears itself; on disconnect the server explicitly
releases every lock held by the disappearing client.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.dependencies import get_ws_store
from app.auth.cookie import COOKIE_NAME
from app.auth.jwt import decode_token
from app.core.config import Settings
from app.db import models as orm
from app.realtime.broker import RealtimeBroker
from app.realtime.events import Actor, EventType, build_envelope
from app.realtime.locks import LockStore
from app.realtime.manager import ConnectionInfo, ConnectionManager

router = APIRouter(tags=["realtime"])
logger = logging.getLogger(__name__)


_CLOSE_POLICY_VIOLATION = 1008
LOCK_TTL_SECONDS = 30


async def _resolve_actor(
    websocket: WebSocket, campaign_id: UUID, settings: Settings
) -> tuple[Actor | None, orm.CampaignRole | None]:
    """Authenticate the connecting socket and return (actor, role).

    When ``AUTH_ENABLED=false`` an anonymous actor is allowed. Otherwise the
    access_token cookie must decode to a user that is a campaign member.
    """
    if not settings.auth_enabled:
        return None, None

    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        await websocket.close(code=_CLOSE_POLICY_VIOLATION, reason="Not authenticated")
        return None, None
    user_id = decode_token(token, settings)
    if user_id is None:
        await websocket.close(code=_CLOSE_POLICY_VIOLATION, reason="Invalid token")
        return None, None

    factory = getattr(websocket.app.state, "session_factory", None)
    if factory is None:
        await websocket.close(code=_CLOSE_POLICY_VIOLATION, reason="Auth backend unavailable")
        return None, None

    async with factory() as db:
        user = await db.get(orm.User, user_id)
        if user is None:
            await websocket.close(code=_CLOSE_POLICY_VIOLATION, reason="User not found")
            return None, None
        result = await db.execute(
            select(orm.CampaignMember).where(
                orm.CampaignMember.campaign_id == campaign_id,
                orm.CampaignMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            await websocket.close(code=_CLOSE_POLICY_VIOLATION, reason="Not a campaign member")
            return None, None
        actor: Actor = {
            "user_id": str(user.id),
            "display_name": user.display_name,
            "role": member.role.value,
        }
        return actor, member.role


def _parse_object_id(payload: dict) -> UUID | None:
    raw = payload.get("object_id")
    if not isinstance(raw, str):
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


async def _handle_lock_acquire(
    *,
    map_id: UUID,
    info: ConnectionInfo,
    payload: dict,
    lock_store: LockStore,
    broker: RealtimeBroker,
    manager: ConnectionManager,
) -> None:
    object_id = _parse_object_id(payload)
    if object_id is None:
        return
    holder_display = info.actor.get("display_name") if info.actor else None
    lock = await lock_store.acquire(
        map_id=map_id,
        object_id=object_id,
        holder_client_id=info.client_id,
        holder_display_name=holder_display,
        ttl_seconds=LOCK_TTL_SECONDS,
    )
    if lock is None:
        # Someone else holds it — only inform the requester.
        await manager.send_to(
            info,
            build_envelope(
                EventType.LOCK_DENIED,
                map_id,
                actor=info.actor,
                payload={"object_id": str(object_id)},
            ),
        )
        return
    await broker.publish(
        map_id,
        build_envelope(
            EventType.LOCK_ACQUIRED,
            map_id,
            actor=info.actor,
            payload=lock.to_payload(),
        ),
    )


async def _handle_lock_release(
    *,
    map_id: UUID,
    info: ConnectionInfo,
    payload: dict,
    lock_store: LockStore,
    broker: RealtimeBroker,
) -> None:
    object_id = _parse_object_id(payload)
    if object_id is None:
        return
    released = await lock_store.release(
        map_id=map_id,
        object_id=object_id,
        holder_client_id=info.client_id,
    )
    if not released:
        return
    await broker.publish(
        map_id,
        build_envelope(
            EventType.LOCK_RELEASED,
            map_id,
            actor=info.actor,
            payload={"object_id": str(object_id), "client_id": info.client_id},
        ),
    )


async def _handle_lock_refresh(
    *,
    map_id: UUID,
    info: ConnectionInfo,
    payload: dict,
    lock_store: LockStore,
) -> None:
    object_id = _parse_object_id(payload)
    if object_id is None:
        return
    await lock_store.refresh(
        map_id=map_id,
        object_id=object_id,
        holder_client_id=info.client_id,
        ttl_seconds=LOCK_TTL_SECONDS,
    )


@router.websocket("/ws/campaigns/{campaign_id}/maps/{map_id}")
async def map_updates(websocket: WebSocket, campaign_id: UUID, map_id: UUID) -> None:
    settings: Settings = websocket.app.state.settings
    store = get_ws_store(websocket)
    manager: ConnectionManager = websocket.app.state.realtime_manager
    broker: RealtimeBroker = websocket.app.state.realtime_broker
    lock_store: LockStore = websocket.app.state.lock_store

    campaign_map = await store.get_map(map_id)
    if campaign_map is None or campaign_map.campaign_id != campaign_id:
        await websocket.close(code=_CLOSE_POLICY_VIOLATION, reason="Map not found")
        return

    actor, _role = await _resolve_actor(websocket, campaign_id, settings)
    if settings.auth_enabled and actor is None:
        return  # close already sent by _resolve_actor

    await websocket.accept()

    client_id = uuid4().hex
    actor_with_client: Actor | None = None
    if actor is not None:
        actor_with_client = {**actor, "client_id": client_id}

    info = ConnectionInfo(websocket=websocket, client_id=client_id, actor=actor_with_client)
    await manager.register(map_id, info)

    try:
        # 1) Confirm connection to the new socket.
        await manager.send_to(
            info,
            build_envelope(
                EventType.MAP_CONNECTED,
                map_id,
                actor=actor_with_client,
                payload={"client_id": client_id},
            ),
        )

        # 2) Send a presence snapshot of everyone currently connected locally.
        await manager.send_to(
            info,
            build_envelope(
                EventType.PRESENCE_SNAPSHOT,
                map_id,
                payload={"actors": manager.snapshot(map_id)},
            ),
        )

        # 3) Send a snapshot of currently held locks so the new client can
        #    grey out objects that are already being edited.
        active_locks = await lock_store.list_for_map(map_id)
        await manager.send_to(
            info,
            build_envelope(
                EventType.LOCK_SNAPSHOT,
                map_id,
                payload={"locks": [lock.to_payload() for lock in active_locks]},
            ),
        )

        # 4) Broadcast that this client joined.
        await broker.publish(
            map_id,
            build_envelope(
                EventType.PRESENCE_JOINED,
                map_id,
                actor=actor_with_client,
                payload={"client_id": client_id},
            ),
            skip_client_id=client_id,
        )

        # 5) Read loop.
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type")

            if event_type == "lock.acquire":
                await _handle_lock_acquire(
                    map_id=map_id,
                    info=info,
                    payload=payload,
                    lock_store=lock_store,
                    broker=broker,
                    manager=manager,
                )
                continue
            if event_type == "lock.release":
                await _handle_lock_release(
                    map_id=map_id,
                    info=info,
                    payload=payload,
                    lock_store=lock_store,
                    broker=broker,
                )
                continue
            if event_type == "lock.refresh":
                await _handle_lock_refresh(
                    map_id=map_id,
                    info=info,
                    payload=payload,
                    lock_store=lock_store,
                )
                continue

            envelope = build_envelope(
                event_type or "map.updated",
                map_id,
                actor=actor_with_client,
                payload=payload,
            )
            await broker.publish(map_id, envelope, skip_client_id=client_id)

    except WebSocketDisconnect:
        pass
    finally:
        # Release every lock held by this client and broadcast each
        # release so other clients can reclaim those objects immediately.
        try:
            released = await lock_store.release_all_for_client(client_id)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to release locks for client %s", client_id)
            released = []
        for lock in released:
            await broker.publish(
                map_id,
                build_envelope(
                    EventType.LOCK_RELEASED,
                    map_id,
                    actor=actor_with_client,
                    payload={
                        "object_id": str(lock.object_id),
                        "client_id": client_id,
                    },
                ),
            )

        await manager.unregister(map_id, info)
        await broker.publish(
            map_id,
            build_envelope(
                EventType.PRESENCE_LEFT,
                map_id,
                actor=actor_with_client,
                payload={"client_id": client_id},
            ),
            skip_client_id=client_id,
        )
