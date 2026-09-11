from fastapi.testclient import TestClient

from boomi_builder.main import create_app


def test_health() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "boomi-builder-api",
        "version": "0.1.0",
    }