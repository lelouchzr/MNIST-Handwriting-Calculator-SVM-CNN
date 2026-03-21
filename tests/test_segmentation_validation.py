"""Ensure the audit rejects a lost good case even when aggregate accuracy is flat."""

import copy
import json
from pathlib import Path

import pytest
from benchmark import iou
from pen_data import expression_cases
from validate_segmentation import FRESH_SEEDS, paired_outcomes

from inkcalc.segmentation import segment_strokes


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
def test_paired_gate_also_rejects_more_errors_on_an_already_wrong_expression(model):
    before = {"expression_records": [outcome(False, "7+2")]}
    after = copy.deepcopy(before)
    after["expression_records"][0]["predictions"][model] = "9-3"
    with pytest.raises(ValueError, match=f"{model}: character errors increased"):
        paired_outcomes(before, after)


@pytest.mark.parametrize("corpus", ["original", "fresh"])
def test_committed_fix_report_satisfies_paired_guards(corpus):
    path = Path(__file__).resolve().parents[1] / "models/segmentation_fix.json"
    report = json.loads(path.read_text())[corpus]
    assert paired_outcomes(report["before"], report["after"]) == report["paired"]


@pytest.mark.parametrize("seed", FRESH_SEEDS)
def test_fresh_corpus_keeps_every_successful_published_segmentation(seed):
    path = Path(__file__).resolve().parents[1] / "models/segmentation_fix.json"
    report = json.loads(path.read_text())
    start = FRESH_SEEDS.index(seed) * 600
    records = report["fresh"]["after"]["expression_records"][start : start + 600]
    for index, (case, recorded) in enumerate(
        zip(expression_cases(seed, 600), records, strict=True)
    ):
        assert case["expression"] == recorded["expected"]
        if not recorded["segmentation_ok"]:
            continue  # The remaining known failure may improve in a future change.
        segments = segment_strokes(case["strokes"])
        assert len(segments) == len(case["boxes"]), (seed, index)
        assert all(
            iou(segment.box, box) >= 0.5
            for segment, box in zip(segments, case["boxes"], strict=True)
        ), (seed, index)
