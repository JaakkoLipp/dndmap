def create_campaign(client) -> dict:
    response = client.post("/api/v1/campaigns", json={"name": "Northreach"})
    assert response.status_code == 201
    return response.json()


def create_map(client, campaign_id: str) -> dict:
    response = client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={"name": "Gloamwood", "width": 2400, "height": 1800},
    )
    assert response.status_code == 201
    return response.json()


def test_map_websocket_broadcasts_update_events(client):
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    with client.websocket_connect(f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "map.connected"
        assert connected["map_id"] == campaign_map["id"]

        ws.send_json({"type": "object.moved", "object_id": "marker-1", "x": 5})
        event = ws.receive_json()

    assert event["type"] == "object.moved"
    assert event["payload"]["object_id"] == "marker-1"
    assert event["map_id"] == campaign_map["id"]
