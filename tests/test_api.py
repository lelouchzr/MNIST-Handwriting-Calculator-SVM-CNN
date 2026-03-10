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
    assert "zero" in response.json()["detail"]


@pytest.mark.parametrize("strokes", [[], [[]], [[[-1, 2]]], [[[0, 1001]]], [[[1]]]])
def test_invalid_ink_is_rejected(client, strokes):
    assert client.post("/api/recognize", json={"strokes": strokes}).status_code == 422


def test_missing_model_keeps_calculator_available(client):
    app.state.recognizer = None
    app.state.model_error = "Model missing."
    assert client.get("/api/health").json()["recognition_ready"] is False
    assert (
        client.post("/api/recognize", json={"strokes": [[[20, 20], [20, 80]]]}).status_code == 503
    )
    assert client.post("/api/calculate", json={"expression": "2+2"}).json()["result"] == "4"
    assert (
        client.post("/api/explain", json={"strokes": [[[20, 20]]], "symbol_index": 0}).status_code
        == 503
    )


def test_explanation_api(client):
    response = client.post(
        "/api/explain",
        json={
            "strokes": [[[20, 50], [90, 50]], [[55, 20], [55, 80]]],
            "symbol_index": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "+"
    assert data["windows"] == 576
    assert len(data["sensitivity"]) == 28
    assert all(len(row) == 28 for row in data["sensitivity"])


@pytest.mark.parametrize("index", [-1, 1, 64, 0.5, True])
def test_invalid_explanation_selection_is_rejected(client, index):
    response = client.post("/api/explain", json={"strokes": [[[20, 20]]], "symbol_index": index})
    assert response.status_code == 422
