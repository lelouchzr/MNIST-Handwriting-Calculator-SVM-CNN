"""Check published metrics against the individual frozen expression outcomes."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "models"


@pytest.mark.parametrize("stage", ["before", "after"])
def test_expression_metrics_match_recorded_cases(stage):
    report = json.loads((ROOT / f"algorithm_{stage}.json").read_text())
    comparison = json.loads((ROOT / "algorithm_comparison.json").read_text())
    assert report["protocol"] == comparison["protocol"]
    records = report["expression_records"]
    assert len(records) == 240
    for profile, metric in report["segmentation"].items():
        cases = [r for r in records if profile == "all" or r["profile"] == profile]
        correct = sum(r["segmentation_ok"] for r in cases)
        assert metric["correct"] == correct
        assert metric["samples"] == len(cases)
        assert metric["accuracy"] == pytest.approx(correct / len(cases))
        assert comparison["segmentation"][stage][profile] == metric
        for model in ("svm", "cnn"):
            exact = sum(r["predictions"][model] == r["expected"] for r in cases)
            result = report["models"][model][f"expressions_{profile}"]
            assert result["correct"] == exact
            assert result["accuracy"] == pytest.approx(exact / len(cases))
            assert (
                comparison["models"][model][f"expressions_{profile}"][stage] == result["accuracy"]
            )
