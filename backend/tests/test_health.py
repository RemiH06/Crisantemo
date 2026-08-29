from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_info(client):
    response = client.get("/api/v1/model-info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"]
    assert body["feature_names"]
