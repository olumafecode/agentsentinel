"""Health endpoints for the container and Kubernetes probes (US-16.4)."""


def test_healthz_reports_the_process_is_up(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_the_data_is_loaded(client, store):
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["seed"] == store.seed
    assert body["customers"] == 43
