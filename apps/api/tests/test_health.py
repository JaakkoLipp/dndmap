def test_health_is_exposed_at_root_and_api_prefix(client):
    root_response = client.get("/health")
    prefixed_response = client.get("/api/v1/health")

    assert root_response.status_code == 200
    assert prefixed_response.status_code == 200
    assert root_response.json()["status"] == "ok"
    assert prefixed_response.json()["environment"] == "test"

