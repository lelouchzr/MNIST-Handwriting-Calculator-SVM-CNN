import base64
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from inkcalc.explanation import occlusion_sensitivity
from inkcalc.recognition import Recognizer

PLUS = [[(20, 50), (90, 50)], [(55, 20), (55, 80)]]


@pytest.fixture(scope="module")
def recognizer():
    return Recognizer()


@pytest.mark.parametrize("direction", [-1, 1])
def test_signed_masking_keeps_coordinates_and_batches_predictions(monkeypatch, direction):
    # A known classifier makes the expected signed effect independently calculable.
    monkeypatch.setattr("inkcalc.explanation.features_from_pixels", lambda pixels: pixels.ravel())

    class MeanClassifier:
        def __init__(self):
            self.calls = []

        def predict_proba(self, samples):
            samples = np.asarray(samples)
            self.calls.append(samples.copy())
            score = 0.5 + direction * 0.25 * samples.mean(axis=1)
            return np.column_stack([score, 1 - score])

    model = MeanClassifier()
    pixels = np.ones((28, 28), dtype=np.float32)
    result = occlusion_sensitivity(pixels, model, 0)
    expected = direction * 0.25 * 25 / (28 * 28)
    np.testing.assert_allclose(result["sensitivity"], expected, atol=1e-7)
    assert [len(batch) for batch in model.calls] == [1, 576]
    first_mask = np.ones((28, 28))
    first_mask[:5, :5] = 0
    last_mask = np.ones((28, 28))
    last_mask[-5:, -5:] = 0
    np.testing.assert_array_equal(model.calls[1][0].reshape(28, 28), first_mask)
    np.testing.assert_array_equal(model.calls[1][-1].reshape(28, 28), last_mask)
    assert result["patch_size"] == 5
    assert np.isfinite(result["sensitivity"]).all()
    np.testing.assert_array_equal(pixels, np.ones((28, 28)))


def test_recognition_exposes_all_classes_and_input_images(recognizer):
    token = recognizer.recognize(PLUS)[0]
    assert token["predicted_label"] == token["label"] == "+"
    assert token["method"] == "classifier"
    probabilities = token["probabilities"]
    assert len(probabilities) == 16
    assert len({item["label"] for item in probabilities}) == 16
    assert sum(item["confidence"] for item in probabilities) == pytest.approx(1)
    assert probabilities == sorted(probabilities, key=lambda item: -item["confidence"])
    data = base64.b64decode(token["input"]["normalized"].split(",")[1])
    image = Image.open(BytesIO(data))
    assert image.size == (28, 28)
    assert image.mode == "L"


def test_explanation_uses_original_prediction_without_changing_model(recognizer):
    before = recognizer.recognize(PLUS)[0]
    result = recognizer.explain(PLUS, 0)
    assert result["supported"] is True
    assert result["label"] == before["predicted_label"]
    assert result["baseline_confidence"] == pytest.approx(before["confidence"])
    assert np.asarray(result["sensitivity"]).shape == (28, 28)
    assert result["max_abs_change"] > 0
    assert recognizer.recognize(PLUS) == [before]


@pytest.mark.parametrize("index", [1])
def test_explanation_rejects_missing_symbols(recognizer, index):
    with pytest.raises(ValueError, match="selected symbol"):
        recognizer.explain(PLUS, index)
