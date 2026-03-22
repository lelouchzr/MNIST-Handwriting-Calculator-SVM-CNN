"""Small, explicit regressions; randomized corpora live in benchmarks/."""

import json
from pathlib import Path

import numpy as np
import pytest

from inkcalc.segmentation import segment_strokes

FIXTURES = Path(__file__).parent / "fixtures"
REGRESSIONS = json.loads((FIXTURES / "interrupted_strokes.json").read_text())
REGRESSIONS.append(json.loads((FIXTURES / "tight_digits.json").read_text()))


@pytest.mark.parametrize("case", REGRESSIONS, ids=lambda case: case["expression"])
def test_recorded_failures_keep_the_expected_symbol_boundaries(case):
    segments = segment_strokes(case["strokes"])
    assert len(segments) == len(case["boxes"])
    np.testing.assert_allclose([segment.box for segment in segments], case["boxes"])


def test_nearby_minuses_remain_distinct():
    assert len(segment_strokes([[(10, 40), (30, 40)], [(35, 40), (55, 40)]])) == 2


def test_disconnected_glyphs_with_overlapping_x_bounds_remain_distinct():
    strokes = [[(10, 10), (35, 10), (10, 60)], [(34, 30), (54, 30), (54, 65)]]
    assert len(segment_strokes(strokes)) == 2


def test_decimal_next_to_digit_is_not_swallowed():
    segments = segment_strokes([[(10, 10), (10, 80)], [(16, 80)]])
    assert len(segments) == 2
    assert not segments[0].is_point
    assert segments[1].is_point


def test_interruptions_follow_pen_tangents():
    assert len(segment_strokes([[(10, 10), (30, 40)], [(33, 44.5), (55, 78)]])) == 1


def test_one_dot_near_a_minus_does_not_make_division():
    assert len(segment_strokes([[(10, 45), (80, 45)], [(46, 70)]])) == 2


def test_tiny_elongated_minus_is_not_a_decimal():
    assert not segment_strokes([[(10, 40), (20, 40)]])[0].is_point


def test_fractional_pixel_rounding_does_not_fuse_vertical_neighbors():
    assert len(segment_strokes([[(10, 10), (10, 80)], [(13.5, 10), (13.5, 80)]])) == 2


def test_sorting_does_not_depend_on_pen_order():
    strokes = [[(120, 10), (120, 80)], [(10, 45), (80, 45)], [(45, 10), (45, 80)]]
    assert [segment.box[0] for segment in segment_strokes(strokes)] == [10, 120]


def test_extreme_bounds_are_rejected():
    with pytest.raises(ValueError, match="bounds"):
        segment_strokes([[(0, 0), (100000, 50)]])
