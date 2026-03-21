"""Geometric regressions independent of model weights or benchmark templates."""

import json
from pathlib import Path

import numpy as np
import pytest
from segmentation_cases import junction_cases

from inkcalc.segmentation import segment_strokes

REGRESSIONS = json.loads((Path(__file__).parent / "fixtures/interrupted_strokes.json").read_text())
JUNCTION_CASES = list(junction_cases())
TIGHT_DIGITS = json.loads((Path(__file__).parent / "fixtures/tight_digits.json").read_text())


@pytest.mark.parametrize("scale", [0.85, 1.0, 1.15])
@pytest.mark.parametrize("shift", [0.0, 0.25, 0.5, 0.75])
def test_subpixel_translation_does_not_fuse_the_recorded_six_and_four(scale, shift):
    strokes = [(np.asarray(stroke) * scale + shift).tolist() for stroke in TIGHT_DIGITS["strokes"]]
    segments = segment_strokes(strokes)
    assert len(segments) == len(TIGHT_DIGITS["boxes"])
    np.testing.assert_allclose(
        [segment.box for segment in segments], np.asarray(TIGHT_DIGITS["boxes"]) * scale + shift
    )


@pytest.mark.parametrize("gap", [3.25, 3.5, 3.75])
@pytest.mark.parametrize("shift", [0.0, 0.25, 0.5, 0.75])
def test_rounding_cannot_connect_separate_vertical_strokes(gap, shift):
    strokes = [
        [(10 + shift, 10), (10 + shift, 80)],
        [(10 + shift + gap, 10), (10 + shift + gap, 80)],
    ]
    assert len(segment_strokes(strokes)) == 2


def test_close_strokes_inside_the_pen_radius_can_still_connect():
    assert len(segment_strokes([[(10, 10), (10, 80)], [(12.75, 10), (12.75, 80)]])) == 1


@pytest.mark.parametrize("case", REGRESSIONS, ids=lambda case: case["expression"])
@pytest.mark.parametrize("scale", [0.85, 1.0, 1.15])
@pytest.mark.parametrize("reverse", [False, True])
def test_recorded_interrupted_ones_rejoin_without_merging_neighbors(case, scale, reverse):
    strokes = [(np.asarray(stroke) * scale + 7.25).tolist() for stroke in case["strokes"]]
    if reverse:
        strokes = [stroke[::-1] for stroke in strokes[::-1]]
    segments = segment_strokes(strokes)
    assert len(segments) == len(case["boxes"])
    np.testing.assert_allclose(
        [segment.box for segment in segments], np.asarray(case["boxes"]) * scale + 7.25
    )


@pytest.mark.parametrize("profile", sorted({case["profile"] for case in JUNCTION_CASES}))
def test_randomized_junctions_and_separate_neighbor_controls(profile):
    for index, case in enumerate(JUNCTION_CASES):
        if case["profile"] != profile:
            continue
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"]), (profile, index)
        np.testing.assert_allclose(
            [segment.box for segment in segments], case["boxes"], err_msg=f"{profile}: {index}"
        )


def test_nearby_minuses_remain_distinct():
    strokes = [[(10, 40), (30, 40)], [(35, 40), (55, 40)]]
    assert len(segment_strokes(strokes)) == 2


def test_overlapping_x_bounds_do_not_merge_disconnected_glyphs():
    strokes = [[(10, 10), (35, 10), (10, 60)], [(34, 30), (54, 30), (54, 65)]]
    assert len(segment_strokes(strokes)) == 2


def test_decimal_next_to_digit_is_not_swallowed():
    strokes = [[(10, 10), (10, 80)], [(16, 80)]]
    segments = segment_strokes(strokes)
    assert len(segments) == 2
    assert not segments[0].is_point
    assert segments[1].is_point


@pytest.mark.parametrize("start_y", [44, 44.5])
def test_interruptions_follow_pen_tangents(start_y):
    strokes = [[(10, 10), (30, 40)], [(33, start_y), (55, 78)]]
    assert len(segment_strokes(strokes)) == 1


def test_small_detached_foot_can_join_a_vertical_digit():
    strokes = [[(20, 10), (20, 65)], [(10, 71), (32, 71)]]
    assert len(segment_strokes(strokes)) == 1


def test_one_dot_near_a_minus_does_not_make_division():
    strokes = [[(10, 45), (80, 45)], [(46, 70)]]
    segments = segment_strokes(strokes)
    assert len(segments) == 2
    assert segments[1].is_point


def test_two_division_dots_may_be_slightly_misaligned():
    strokes = [[(10, 45), (80, 47)], [(42, 15)], [(49, 77)]]
    assert len(segment_strokes(strokes)) == 1


def test_tiny_elongated_minus_is_not_a_decimal():
    assert not segment_strokes([[(10, 40), (20, 40)]])[0].is_point


def test_sorting_does_not_depend_on_pen_order():
    strokes = [[(120, 10), (120, 80)], [(10, 45), (80, 45)], [(45, 10), (45, 80)]]
    assert [segment.box[0] for segment in segment_strokes(strokes)] == [10, 120]


def test_empty_strokes_are_handled():
    assert segment_strokes([]) == []


def test_extreme_bounds_are_rejected():
    with pytest.raises(ValueError, match="bounds"):
        segment_strokes([[(0, 0), (100000, 50)]])
