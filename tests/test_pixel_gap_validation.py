"""Keep the newly evaluated holdout as regression coverage for future geometry changes."""

import json
from pathlib import Path

import pytest
from benchmark import iou
from pen_data import expression_cases
from segmentation_cases import pixel_gap_cases
from validate_pixel_gaps import FRESH_SEEDS, PIXEL_SEED
from validate_segmentation import paired_outcomes

from inkcalc.segmentation import segment_strokes

REPORT = json.loads((Path(__file__).resolve().parents[1] / "models/pixel_gap_fix.json").read_text())


@pytest.mark.parametrize("corpus", ["original", "previous_holdout", "fresh"])
def test_published_pixel_guard_audit_has_no_individual_regressions(corpus):
    result = REPORT[corpus]
    assert paired_outcomes(result["before"], result["after"]) == result["paired"]


@pytest.mark.parametrize("seed", FRESH_SEEDS)
def test_new_expression_holdout_remains_correctly_segmented(seed):
    for index, case in enumerate(expression_cases(seed, 600)):
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"]), (seed, index)
        assert all(
            iou(segment.box, box) >= 0.5
            for segment, box in zip(segments, case["boxes"], strict=True)
        ), (seed, index)


def test_independent_pixel_controls_preserve_both_separation_and_contacts():
    for index, case in enumerate(pixel_gap_cases(PIXEL_SEED)):
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"]), (case["profile"], index)
        assert all(
            iou(segment.box, box) >= 0.5
            for segment, box in zip(segments, case["boxes"], strict=True)
        ), (case["profile"], index)
