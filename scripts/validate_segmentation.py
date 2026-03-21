"""Audit a segmentation-only fix against the prior release and untouched fresh seeds."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from benchmark import distance, evaluate, evaluation_data, fingerprint, iou
from pen_data import expression_cases
from segmentation_cases import junction_cases

from inkcalc.recognition import Recognizer

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "cb7a7317305ddaa9d9a6de865787bf42740b0761"
FRESH_SEEDS = (314159, 271828, 161803)
JUNCTION_SEED = 515151


def previous_segmenter(revision=PREVIOUS):
    """Load the committed previous geometry without changing the current checkout."""
    source = subprocess.check_output(
        ["git", "show", f"{revision}:src/inkcalc/segmentation.py"], cwd=ROOT
    )
    path = ROOT / f".cache/segmentation-{revision[:12]}.py"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location(f"segmentation_{revision[:12]}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.segment_strokes


def paired_outcomes(before, after):
    """Count individual regressions; aggregate gains cannot hide a lost good case."""
    checks = {}
    pairs = list(zip(before["expression_records"], after["expression_records"], strict=True))
    for target in ("segmentation", "svm", "cnn"):
        gained, regressed, retained = [], [], 0
        for index, (old, new) in enumerate(pairs):
            if (old["profile"], old["expected"]) != (new["profile"], new["expected"]):
                raise ValueError("Paired expression inputs differ.")
            was_correct = (
                old["segmentation_ok"]
                if target == "segmentation"
                else old["predictions"][target] == old["expected"]
            )
            is_correct = (
                new["segmentation_ok"]
                if target == "segmentation"
                else new["predictions"][target] == new["expected"]
            )
            if was_correct and is_correct:
                retained += 1
            elif was_correct:
                regressed.append(index)
            elif is_correct:
                gained.append(index)
        checks[target] = {
            "retained_correct": retained,
            "newly_correct_indices": gained,
            "regressed_indices": regressed,
        }
        if regressed:
            raise ValueError(f"{target}: previously correct cases regressed: {regressed}")
        if target != "segmentation":
            increased = [
                index
                for index, (old, new) in enumerate(pairs)
                if distance(old["expected"], old["predictions"][target])
                < distance(new["expected"], new["predictions"][target])
            ]
            checks[target]["increased_edit_distance_indices"] = increased
            if increased:
                raise ValueError(f"{target}: character errors increased for cases: {increased}")
    for model in ("svm", "cnn"):
        for profile, metric in before["models"][model].items():
            if (
                metric["character_error_rate"]
                < after["models"][model][profile]["character_error_rate"]
            ):
                raise ValueError(f"{model}: character error rate increased for {profile}.")
    return checks


def geometry_audit(before_segment, after_segment):
    cases = list(junction_cases(JUNCTION_SEED))
    outcomes = []
    metrics = {"before": {}, "after": {}}
    for index, case in enumerate(cases):
        record = {"index": index, "profile": case["profile"]}
        for stage, segment in (("before", before_segment), ("after", after_segment)):
            segments = segment(case["strokes"])
            ok = len(segments) == len(case["boxes"]) and all(
                iou(item.box, box) >= 0.5 for item, box in zip(segments, case["boxes"], strict=True)
            )
            record[stage] = bool(ok)
            metric = metrics[stage].setdefault(case["profile"], {"correct": 0, "samples": 0})
            metric["correct"] += int(ok)
            metric["samples"] += 1
        outcomes.append(record)
    regressions = [r["index"] for r in outcomes if r["before"] and not r["after"]]
    if regressions or not all(r["after"] for r in outcomes):
        raise ValueError(f"Fresh junction controls failed: {regressions}")
    return {
        "seed": JUNCTION_SEED,
        "fingerprint": fingerprint({}, cases),
        "metrics": metrics,
        "regressed_indices": regressions,
        "outcomes": outcomes,
    }


def main():
    after = Recognizer()
    before = copy.copy(after)
    before.segment = previous_segmenter()
    # The models must be byte-identical; this audit isolates the segmentation change.
    weights = {}
    for name in ("symbols.joblib", "cnn.pt"):
        path = ROOT / "models" / name
        previous = subprocess.check_output(["git", "show", f"{PREVIOUS}:models/{name}"], cwd=ROOT)
        if previous != path.read_bytes():
            raise ValueError(f"Model {name} changed; this is no longer a geometry-only audit.")
        weights[name] = hashlib.sha256(previous).hexdigest()
    datasets, original_cases = evaluation_data()
    stored = json.loads(
        subprocess.check_output(
            ["git", "show", f"{PREVIOUS}:models/algorithm_after.json"], cwd=ROOT
        )
    )
    if fingerprint(datasets, original_cases) != stored["protocol"]["fingerprint"]:
        raise ValueError("Original benchmark input fingerprint changed.")
    original_before = evaluate(before, {}, original_cases)
    for model in ("svm", "cnn"):
        for name, metric in original_before["models"][model].items():
            if metric != stored["models"][model][name]:
                raise ValueError("Previous release does not reproduce its recorded results.")
    original_after = evaluate(after, datasets, original_cases)
    for model in ("svm", "cnn"):
        for dataset in datasets:
            metric = json.loads(json.dumps(original_after["models"][model][dataset]))
            if metric != stored["models"][model][dataset]:
                raise ValueError("Isolated-symbol classification changed.")
    original_pairs = paired_outcomes(original_before, original_after)
    fixed = [
        index
        for index, (old, new) in enumerate(
            zip(
                original_before["expression_records"],
                original_after["expression_records"],
                strict=True,
            )
        )
        if not old["segmentation_ok"] and new["segmentation_ok"]
    ]
    if fixed != [52, 136, 196]:
        raise ValueError(
            f"Expected all three recorded segmentation regressions to be fixed: {fixed}"
        )
    fresh_cases = [
        {**case, "seed": seed} for seed in FRESH_SEEDS for case in expression_cases(seed, 600)
    ]
    fresh_before = evaluate(before, {}, fresh_cases)
    fresh_after = evaluate(after, {}, fresh_cases)
    fresh_pairs = paired_outcomes(fresh_before, fresh_after)
    geometry = geometry_audit(before.segment, after.segment)
    report = {
        "protocol": {
            "previous_revision": PREVIOUS,
            "fresh_expression_seeds": FRESH_SEEDS,
            "expressions_per_seed": 600,
            "fresh_expression_fingerprint": fingerprint({}, fresh_cases),
            "model_sha256": weights,
            "selection_policy": (
                "Known regressions and geometry probes seed 424242 used in development; "
                "fresh seeds evaluated after freezing the fix; no tuning on fresh outcomes."
            ),
            "limitations": "All fresh stroke cases are synthetic; no new human-handwriting claim.",
        },
        "original": {
            "before": original_before,
            "after": original_after,
            "paired": original_pairs,
        },
        "fresh": {"before": fresh_before, "after": fresh_after, "paired": fresh_pairs},
        "junction_controls": geometry,
    }
    destination = ROOT / "models/segmentation_fix.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                name: {
                    "segmentation": result["after"]["segmentation"]["all"],
                    "expressions": {
                        model: result["after"]["models"][model]["expressions_all"]
                        for model in ("svm", "cnn")
                    },
                    "paired": result["paired"],
                }
                for name, result in (("original", report["original"]), ("fresh", report["fresh"]))
            },
            indent=2,
        ),
        flush=True,
    )
    print("Fresh geometric controls: 800/800; report:", destination, flush=True)


if __name__ == "__main__":
    main()
