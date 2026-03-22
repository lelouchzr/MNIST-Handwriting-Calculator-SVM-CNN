"""Checks for the benchmark's paired comparison gate, outside application CI."""

import copy

import pytest

from benchmarks.junctions import paired_outcomes


def outcome(segmentation_ok, prediction):
    return {
        "profile": "broken",
        "expected": "1+2",
        "segmentation_ok": segmentation_ok,
        "predictions": {"svm": prediction, "cnn": prediction},
    }


@pytest.mark.parametrize("target", ["segmentation", "svm", "cnn"])
def test_paired_gate_rejects_a_regression_offset_by_a_gain(target):
    before = {"expression_records": [outcome(True, "1+2"), outcome(False, "7+2")]}
    after = copy.deepcopy(before)
    if target == "segmentation":
        after["expression_records"][0]["segmentation_ok"] = False
        after["expression_records"][1]["segmentation_ok"] = True
    else:
        after["expression_records"][0]["predictions"][target] = "7+2"
        after["expression_records"][1]["predictions"][target] = "1+2"
    with pytest.raises(ValueError, match=f"{target}: previously correct cases regressed"):
        paired_outcomes(before, after)


@pytest.mark.parametrize("model", ["svm", "cnn"])
def test_paired_gate_rejects_more_errors_on_an_already_wrong_expression(model):
    before = {"expression_records": [outcome(False, "7+2")]}
    after = copy.deepcopy(before)
    after["expression_records"][0]["predictions"][model] = "9-3"
    with pytest.raises(ValueError, match=f"{model}: character errors increased"):
        paired_outcomes(before, after)
