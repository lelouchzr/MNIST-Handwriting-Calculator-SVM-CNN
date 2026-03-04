import pytest
from fastapi.testclient import TestClient

from inkcalc.api import app


@pytest.fixture
def client():
    with TestClient(app) as session:
        yield session


def test_calculation_api(client):
    response = client.post("/api/calculate", json={"expression": "(12+3)*2"})
    assert response.status_code == 200
    assert response.json()["result"] == "30"


def test_invalid_calculation_is_actionable(client):
    response = client.post("/api/calculate", json={"expression": "1/0"})
    assert response.status_code == 422
    assert "zéro" in response.json()["detail"]


@pytest.mark.parametrize("strokes", [[], [[]], [[[-1, 2]]], [[[0, 1001]]], [[[1]]]])
def test_invalid_ink_is_rejected(client, strokes):
    assert client.post("/api/recognize", json={"strokes": strokes}).status_code == 422


def test_missing_model_keeps_calculator_available(client):
    app.state.recognizer = None
    app.state.model_error = "Modèle absent."
    assert client.get("/api/health").json()["recognition_ready"] is False
    assert (
        client.post("/api/recognize", json={"strokes": [[[20, 20], [20, 80]]]}).status_code == 503
    )
    assert client.post("/api/calculate", json={"expression": "2+2"}).json()["result"] == "4"
