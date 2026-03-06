import numpy as np
import pytest
from PIL import Image, ImageDraw

from inkcalc.features import normalize
from inkcalc.recognition import Recognizer


@pytest.fixture(scope="module")
def recognizer():
    return Recognizer()


def test_disconnected_strokes_form_one_plus(recognizer):
    tokens = recognizer.recognize([[(20, 50), (90, 50)], [(55, 20), (55, 80)]])
    assert len(tokens) == 1
    assert tokens[0]["label"] == "+"
    assert tokens[0]["confidence"] > 0.8


def test_symbols_are_sorted_by_horizontal_position(recognizer):
    tokens = recognizer.recognize([[(200, 50), (280, 50)], [(20, 50), (90, 50)]])
    assert [token["label"] for token in tokens] == ["−", "−"]
    assert tokens[0]["box"][0] < tokens[1]["box"][0]


def test_division_dots_merge_with_bar(recognizer):
    tokens = recognizer.recognize(
        [
            [(20, 50), (90, 50)],
            [(55, 20)],
            [(55, 80)],
        ]
    )
    assert len(tokens) == 1
    assert tokens[0]["label"] == "÷"


def test_isolated_small_mark_is_decimal_point(recognizer):
    assert recognizer.recognize([[(20, 80)]])[0]["label"] == "."


def test_blank_image_normalizes_without_nan():
    pixels = normalize(Image.new("L", (100, 100)))
    assert pixels.shape == (28, 28)
    assert np.isfinite(pixels).all()
    assert not pixels.any()


def test_small_glyph_is_enlarged_and_centered():
    image = Image.new("L", (30, 30))
    ImageDraw.Draw(image).line([(5, 2), (5, 10)], fill=255, width=2)
    pixels = normalize(image)
    ys, xs = np.where(pixels > 0.3)
    assert ys.max() - ys.min() >= 17
    assert abs(xs.mean() - 13.5) < 1


def test_rejects_excessive_number_of_symbols(recognizer):
    with pytest.raises(ValueError, match="64"):
        recognizer.recognize([[(index * 15, 10)] for index in range(65)])
