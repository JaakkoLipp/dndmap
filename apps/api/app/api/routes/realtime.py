from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.api.dependencies import get_ws_store
from app.domain.models import utc_now

router = APIRouter(tags=["realtime"])


class MapConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = {}

    async def connect(self, map_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(map_id, set()).add(websocket)

    def disconnect(self, map_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(map_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(map_id, None)

    async def broadcast(self, map_id: UUID, message: dict) -> None:
        for websocket in list(self._connections.get(map_id, set())):
            await websocket.send_json(message)


manager = MapConnectionManager()


@router.websocket("/ws/campaigns/{campaign_id}/maps/{map_id}")
async def map_updates(websocket: WebSocket, campaign_id: UUID, map_id: UUID) -> None:
    store = get_ws_store(websocket)
    campaign_map = await store.get_map(map_id)
    if campaign_map is None or campaign_map.campaign_id != campaign_id:
        await websocket.close(code=1008, reason="Map not found")
        return

    await manager.connect(map_id, websocket)
    await websocket.send_json(
        jsonable_encoder(
            {
                "type": "map.connected",
                "map_id": map_id,
                "sent_at": utc_now(),
            }
        )
    )

    try:
        while True:
            payload = await websocket.receive_json()
            event = {
                "id": uuid4(),
                "type": payload.get("type", "map.updated"),
                "map_id": map_id,
                "payload": payload,
                "sent_at": utc_now(),
            }
            await manager.broadcast(map_id, jsonable_encoder(event))
    except WebSocketDisconnect:
        manager.disconnect(map_id, websocket)
