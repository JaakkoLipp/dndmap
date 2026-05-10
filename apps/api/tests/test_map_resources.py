import pytest


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
    assert moved.json()["geometry"]["x"] == 380

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


def test_map_image_metadata_round_trips(client):
    campaign = create_campaign(client)

    created = client.post(
        f"/api/v1/campaigns/{campaign['id']}/maps",
        json={
            "name": "Moonwell",
            "width": 1200,
            "height": 900,
            "imageObjectKey": "maps/moonwell.png",
            "imageUrl": "https://assets.example.test/maps/moonwell.png",
            "imageName": "moonwell.png",
            "imageContentType": "image/png",
        },
    )

    assert created.status_code == 201
    campaign_map = created.json()
    assert campaign_map["image_object_key"] == "maps/moonwell.png"
    assert campaign_map["image_url"] == "https://assets.example.test/maps/moonwell.png"
    assert campaign_map["image_name"] == "moonwell.png"
    assert campaign_map["image_content_type"] == "image/png"

    updated = client.patch(
        f"/api/v1/maps/{campaign_map['id']}",
        json={"image_url": None, "image_name": "moonwell-v2.png"},
    )

    assert updated.status_code == 200
    assert updated.json()["image_url"] is None
    assert updated.json()["image_name"] == "moonwell-v2.png"


def test_layer_audience_visibility_and_filters(client):
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    dm_layer = client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        json={"name": "DM Notes", "audience": "dm", "visible": True},
    ).json()
    hidden_player_layer = client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        json={"name": "Hidden Player Layer", "audience": "players", "visible": False},
    ).json()

    assert dm_layer["audience"] == "dm"
    assert hidden_player_layer["visible"] is False

    made_visible = client.patch(
        f"/api/v1/layers/{hidden_player_layer['id']}",
        json={"visible": True},
    )
    assert made_visible.status_code == 200

    player_layers = client.get(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        params={"audience": "players", "visible": True},
    )

    assert player_layers.status_code == 200
    assert [layer["id"] for layer in player_layers.json()] == [
        hidden_player_layer["id"]
    ]


@pytest.mark.parametrize(
    ("kind", "geometry", "style", "expected_style"),
    [
        (
            "marker",
            {"type": "marker", "x": 100, "y": 140, "radius": 16},
            {"color": "#d79b39", "strokeColor": "#fff5dc", "strokeWidth": 2},
            {"color": "#d79b39", "stroke_color": "#fff5dc", "stroke_width": 2},
        ),
        (
            "label",
            {"type": "label", "x": 200, "y": 240, "text": "Secret Door"},
            {"color": "#d7d0bb", "fontSize": 28},
            {"color": "#d7d0bb", "font_size": 28},
        ),
        (
            "line",
            {"type": "line", "points": [{"x": 0, "y": 0}, {"x": 80, "y": 40}]},
            {"strokeColor": "#6aa9b8", "strokeWidth": 5},
            {"stroke_color": "#6aa9b8", "stroke_width": 5},
        ),
        (
            "freehand",
            {
                "type": "freehand",
                "points": [{"x": 0, "y": 0}, {"x": 20, "y": 12}, {"x": 40, "y": 8}],
            },
            {"strokeColor": "#c95f55", "strokeWidth": 4},
            {"stroke_color": "#c95f55", "stroke_width": 4},
        ),
        (
            "polygon",
            {
                "type": "polygon",
                "points": [{"x": 10, "y": 10}, {"x": 80, "y": 10}, {"x": 40, "y": 70}],
            },
            {"fillColor": "#1f2937", "strokeColor": "#fff5dc", "strokeWidth": 3},
            {
                "fill_color": "#1f2937",
                "stroke_color": "#fff5dc",
                "stroke_width": 3,
            },
        ),
        (
            "handout",
            {"type": "handout", "x": 300, "y": 160, "width": 180, "height": 120},
            {"borderColor": "#d7d0bb", "opacity": 0.9},
            {"border_color": "#d7d0bb", "opacity": 0.9},
        ),
    ],
)
def test_typed_annotation_geometry_and_style_round_trip(
    client,
    kind,
    geometry,
    style,
    expected_style,
):
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])
    layer = client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        json={"name": "Annotations", "audience": "players"},
    ).json()

    created = client.post(
        f"/api/v1/maps/{campaign_map['id']}/objects",
        json={
            "layer_id": layer["id"],
            "name": f"{kind.title()} Test",
            "kind": kind,
            "audience": "players",
            "geometry": geometry,
            "style": style,
        },
    )

    assert created.status_code == 201
    map_object = created.json()
    assert map_object["kind"] == kind
    assert map_object["audience"] == "players"
    assert map_object["geometry"]["type"] == kind
    assert map_object["width"] > 0
    assert map_object["height"] > 0
    for key, value in expected_style.items():
        assert map_object["style"][key] == value

    visible_objects = client.get(
        f"/api/v1/maps/{campaign_map['id']}/objects",
        params={"audience": "players", "visible": True},
    )
    assert [item["id"] for item in visible_objects.json()] == [map_object["id"]]


def test_object_geometry_must_match_kind(client):
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])
    layer = client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        json={"name": "Annotations"},
    ).json()

    response = client.post(
        f"/api/v1/maps/{campaign_map['id']}/objects",
        json={
            "layer_id": layer["id"],
            "name": "Bad Shape",
            "kind": "marker",
            "geometry": {
                "type": "polygon",
                "points": [{"x": 0, "y": 0}, {"x": 20, "y": 0}, {"x": 10, "y": 20}],
            },
        },
    )

    assert response.status_code == 422
