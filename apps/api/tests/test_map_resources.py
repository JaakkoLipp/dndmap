def create_campaign(client) -> dict:
    response = client.post("/api/v1/campaigns", json={"name": "Northreach"})
    assert response.status_code == 201
    return response.json()


def create_map(client, campaign_id: str) -> dict:
    response = client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={
            "name": "Gloamwood",
            "width": 2400,
            "height": 1800,
            "grid_size": 60,
            "background_color": "#0f172a",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_map_layer_object_and_export_flow(client):
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    layer_response = client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        json={"name": "Tokens", "kind": "objects", "sort_order": 10},
    )
    assert layer_response.status_code == 201
    layer = layer_response.json()

    object_response = client.post(
        f"/api/v1/maps/{campaign_map['id']}/objects",
        json={
            "layer_id": layer["id"],
            "name": "Ancient Guardian",
            "kind": "marker",
            "x": 320,
            "y": 480,
            "width": 60,
            "height": 60,
            "properties": {"hp": 42, "initiative": 13},
        },
    )
    assert object_response.status_code == 201
    map_object = object_response.json()
    assert map_object["properties"]["hp"] == 42

    moved = client.patch(
        f"/api/v1/objects/{map_object['id']}",
        json={"x": 380, "y": 500, "rotation": 45},
    )
    assert moved.status_code == 200
    assert moved.json()["x"] == 380

    export_response = client.post(
        f"/api/v1/maps/{campaign_map['id']}/exports",
        json={"format": "json", "include_hidden_layers": True},
    )
    assert export_response.status_code == 202
    assert export_response.json()["status"] == "queued"

    listed_objects = client.get(f"/api/v1/maps/{campaign_map['id']}/objects")
    listed_exports = client.get(f"/api/v1/maps/{campaign_map['id']}/exports")
    assert len(listed_objects.json()) == 1
    assert len(listed_exports.json()) == 1


def test_object_layer_must_belong_to_target_map(client):
    campaign = create_campaign(client)
    first_map = create_map(client, campaign["id"])
    second_map = client.post(
        f"/api/v1/campaigns/{campaign['id']}/maps",
        json={"name": "Elsewhere", "width": 800, "height": 800},
    ).json()

    layer = client.post(
        f"/api/v1/maps/{first_map['id']}/layers",
        json={"name": "Wrong Map Layer"},
    ).json()

    response = client.post(
        f"/api/v1/maps/{second_map['id']}/objects",
        json={
            "layer_id": layer["id"],
            "name": "Misplaced Token",
            "kind": "marker",
            "x": 0,
            "y": 0,
            "width": 50,
            "height": 50,
        },
    )

    assert response.status_code == 404
