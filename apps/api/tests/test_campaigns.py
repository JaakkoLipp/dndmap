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

