"""Geometric regressions independent of model weights or benchmark templates."""

import pytest

from inkcalc.segmentation import segment_strokes


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
