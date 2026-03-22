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


@pytest.mark.parametrize("strokes", [[], [[[-1, 2]]]])
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


@pytest.mark.parametrize("index", [-1, 0.5])
def test_invalid_explanation_selection_is_rejected(client, index):
    response = client.post("/api/explain", json={"strokes": [[[20, 20]]], "symbol_index": index})
    assert response.status_code == 422


def test_compare_api_and_model_health(client):
    status = client.get("/api/health").json()
    assert status["models"]["svm"]["ready"] is True
    assert status["models"]["cnn"]["ready"] is True
    strokes = [[[20, 50], [90, 50]], [[55, 20], [55, 80]]]
    response = client.post("/api/recognize", json={"strokes": strokes, "model": "compare"})
    assert response.status_code == 200
    assert response.json()["model"] == "compare"
    assert set(response.json()["tokens"][0]["models"]) == {"svm", "cnn"}
    explanation = client.post(
        "/api/explain", json={"strokes": strokes, "symbol_index": 0, "model": "compare"}
    )
    assert explanation.status_code == 200
    assert set(explanation.json()["models"]) == {"svm", "cnn"}


def test_unknown_model_is_rejected(client):
    assert (
        client.post(
            "/api/recognize", json={"strokes": [[[20, 20]]], "model": "unknown"}
        ).status_code
        == 422
    )
