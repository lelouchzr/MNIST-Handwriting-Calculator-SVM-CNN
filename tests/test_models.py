import json
from pathlib import Path

import numpy as np
import pytest

from inkcalc.cnn import CNNClassifier
from inkcalc.recognition import ModelUnavailableError, Recognizer

PLUS = [[(20, 50), (90, 50)], [(55, 20), (55, 80)]]
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def recognizer():
    return Recognizer()


def test_committed_models_use_identical_train_and_test_inputs():
    svm = json.loads((ROOT / "models/metrics.json").read_text())
    cnn = json.loads((ROOT / "models/cnn_metrics.json").read_text())
    comparison = json.loads((ROOT / "models/comparison.json").read_text())
    for key in ("training_inputs_sha256", "evaluation_inputs_sha256"):
        assert svm[key] == cnn[key] == comparison[key]
    assert svm["mnist_train_samples"] == cnn["mnist_train_samples"] == 20000
    assert cnn["score_kind"] == "uncalibrated_softmax"
    assert svm["score_kind"] == "calibrated_probability"


def test_cnn_is_a_real_convolutional_network_and_inference_is_deterministic():
    import torch

    cnn = CNNClassifier()
    assert sum(isinstance(layer, torch.nn.Conv2d) for layer in cnn.model.modules()) == 2
    pixels = np.random.default_rng(42).random((3, 28, 28)).astype(np.float32)
    first = cnn.predict_proba(pixels)
    assert first.shape == (3, 16)
    assert np.isfinite(first).all()
    np.testing.assert_allclose(first.sum(axis=1), 1, atol=1e-6)
    np.testing.assert_array_equal(first, cnn.predict_proba(pixels))
    assert not cnn.model.training


@pytest.mark.parametrize("shape", [(28, 28), (2, 1, 28, 28), (2, 27, 28)])
def test_cnn_rejects_invalid_input_shapes(shape):
    with pytest.raises(ValueError, match="shape"):
        CNNClassifier().predict_proba(np.zeros(shape))


def test_cnn_rejects_nonfinite_inputs():
    with pytest.raises(ValueError, match="finite"):
        CNNClassifier().predict_proba(np.full((1, 28, 28), np.nan))


def test_compare_predicts_both_models_on_one_segment(recognizer):
    token = recognizer.recognize(PLUS, "compare")[0]
    assert set(token["models"]) == {"svm", "cnn"}
    assert token["label"] == token["models"]["svm"]["predicted_label"]
    for model in ("svm", "cnn"):
        prediction = token["models"][model]
        assert prediction["predicted_label"] == "+"
        assert len(prediction["probabilities"]) == 16
        assert sum(item["confidence"] for item in prediction["probabilities"]) == pytest.approx(1)
    assert token["agreement"] is True


def test_comparison_reports_disagreement_without_overriding_source(recognizer, monkeypatch):
    original = recognizer._prediction

    def prediction(pixels, model, is_point):
        result = original(pixels, model, is_point)
        if model == "cnn":
            result["predicted_label"] = "9"
        return result

    monkeypatch.setattr(recognizer, "_prediction", prediction)
    token = recognizer.recognize(PLUS, "compare")[0]
    assert token["agreement"] is False
    assert token["label"] == "+"
    assert token["models"]["cnn"]["predicted_label"] == "9"


def test_cnn_explanation_matches_its_own_prediction(recognizer):
    prediction = recognizer.recognize(PLUS, "cnn")[0]
    explanation = recognizer.explain(PLUS, 0, "cnn")
    assert explanation["model_id"] == "cnn"
    assert explanation["label"] == prediction["predicted_label"]
    assert explanation["baseline_confidence"] == pytest.approx(prediction["confidence"])
    assert explanation["windows"] == 576
    assert np.asarray(explanation["sensitivity"]).shape == (28, 28)
    assert np.isfinite(explanation["sensitivity"]).all()
    assert explanation["max_abs_change"] > 0


def test_both_explanations_have_a_shared_color_scale(recognizer):
    result = recognizer.explain(PLUS, 0, "compare")
    assert result["shared_max_abs_change"] == max(
        item["max_abs_change"] for item in result["models"].values()
    )
    assert {item["model_id"] for item in result["models"].values()} == {"svm", "cnn"}


def test_decimal_rule_is_not_counted_as_classifier_agreement(recognizer):
    strokes = [[(20, 30)]]
    token = recognizer.recognize(strokes, "compare")[0]
    assert token["agreement"] is None
    assert all(item["probabilities"] == [] for item in token["models"].values())
    result = recognizer.explain(strokes, 0, "compare")
    assert result["shared_max_abs_change"] == 0
    assert all(not item["supported"] for item in result["models"].values())


def test_missing_cnn_keeps_svm_usable(tmp_path):
    recognizer = Recognizer(cnn_path=tmp_path / "missing.pt")
    assert recognizer.models_status["cnn"]["ready"] is False
    assert recognizer.recognize(PLUS)[0]["label"] == "+"
    with pytest.raises(ModelUnavailableError, match="CNN"):
        recognizer.recognize(PLUS, "compare")


def test_missing_svm_keeps_cnn_usable(tmp_path):
    recognizer = Recognizer(path=tmp_path / "missing.joblib")
    assert recognizer.models_status["svm"]["ready"] is False
    assert recognizer.recognize(PLUS, "cnn")[0]["label"] == "+"
