"""Optional randomized geometry checks; run with uv run pytest benchmarks."""

import json
from pathlib import Path

import numpy as np
import pytest

from benchmarks.cases import junction_cases, pixel_gap_cases
from benchmarks.recognition import iou
from inkcalc.segmentation import segment_strokes
from scripts.pen_data import expression_cases

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("seed", [314159, 271828, 161803, 235711, 101317, 192323])
def test_expression_corpora(seed):
    for index, case in enumerate(expression_cases(seed, 600)):
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"]), (seed, index)
        assert all(
            iou(segment.box, box) >= 0.5
            for segment, box in zip(segments, case["boxes"], strict=True)
        ), (seed, index)


@pytest.mark.parametrize("seed", [424242, 515151])
def test_junction_controls(seed):
    for index, case in enumerate(junction_cases(seed)):
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"]), (seed, index)
        np.testing.assert_allclose([s.box for s in segments], case["boxes"])


def test_pixel_controls():
    for case in pixel_gap_cases():
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"])
        np.testing.assert_allclose([s.box for s in segments], case["boxes"])


@pytest.mark.parametrize("scale", [0.85, 1.15])
@pytest.mark.parametrize("shift", [0.25, 0.75])
def test_recorded_failures_under_coordinate_transforms(scale, shift):
    fixtures = ROOT / "tests/fixtures"
    cases = json.loads((fixtures / "interrupted_strokes.json").read_text())
    cases.append(json.loads((fixtures / "tight_digits.json").read_text()))
    for case in cases:
        strokes = [(np.asarray(s) * scale + shift).tolist() for s in case["strokes"]]
        segments = segment_strokes([s[::-1] for s in strokes[::-1]])
        assert len(segments) == len(case["boxes"])
        np.testing.assert_allclose(
            [s.box for s in segments], np.asarray(case["boxes"]) * scale + shift
        )
