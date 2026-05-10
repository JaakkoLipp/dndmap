"""WebSocket endpoint for map collaboration.

Authenticated when ``AUTH_ENABLED=true``: the access_token cookie is decoded
and campaign membership is checked. The endpoint sends a presence snapshot
on connect, broadcasts ``presence.joined``/``presence.left`` events, and
echoes client-sent messages through the realtime broker so they reach every
process subscribed to the same map.

The wire envelope is the standard shape produced by
``app.realtime.events.build_envelope``.
"""

from __future__ import annotations

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
from app.realtime.manager import ConnectionInfo, ConnectionManager

router = APIRouter(tags=["realtime"])


_CLOSE_POLICY_VIOLATION = 1008


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


@router.websocket("/ws/campaigns/{campaign_id}/maps/{map_id}")
async def map_updates(websocket: WebSocket, campaign_id: UUID, map_id: UUID) -> None:
    settings: Settings = websocket.app.state.settings
    store = get_ws_store(websocket)
    manager: ConnectionManager = websocket.app.state.realtime_manager
    broker: RealtimeBroker = websocket.app.state.realtime_broker

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

        # 3) Broadcast that this client joined.
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

        # 4) Read loop — relay client messages onto the broker.
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type", "map.updated")
            envelope = build_envelope(
                event_type,
                map_id,
                actor=actor_with_client,
                payload=payload,
            )
            await broker.publish(map_id, envelope, skip_client_id=client_id)

    except WebSocketDisconnect:
        pass
    finally:
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
