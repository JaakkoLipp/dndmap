def test_campaign_crud(client):
    created = client.post(
        "/api/v1/campaigns",
        json={"name": "Shattered Isles", "description": "Sky islands and ruins."},
    )

    assert created.status_code == 201
    campaign = created.json()
    assert campaign["name"] == "Shattered Isles"

    listed = client.get("/api/v1/campaigns")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [campaign["id"]]

    updated = client.patch(
        f"/api/v1/campaigns/{campaign['id']}",
        json={"description": "A rebuilt description."},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "A rebuilt description."

    deleted = client.delete(f"/api/v1/campaigns/{campaign['id']}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/campaigns/{campaign['id']}")
    assert missing.status_code == 404


def test_campaign_me_returns_synthetic_owner_in_dev_mode(client):
    """When auth is off, /campaigns/{id}/me returns an owner stub for the UI."""
    created = client.post("/api/v1/campaigns", json={"name": "Devmode"})
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    response = client.get(f"/api/v1/campaigns/{campaign_id}/me")
    assert response.status_code == 200
    body = response.json()
    assert body["campaign_id"] == campaign_id
    assert body["role"] == "owner"
