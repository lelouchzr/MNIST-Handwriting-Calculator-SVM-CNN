"""Paired audit of the continuous-coordinate guard, with a new untouched holdout."""

import copy
import hashlib
import json
import subprocess
from pathlib import Path

from benchmarks.cases import junction_cases, pixel_gap_cases
from benchmarks.junctions import paired_outcomes, previous_segmenter
from benchmarks.recognition import evaluate, evaluation_data, fingerprint, iou
from inkcalc.recognition import Recognizer
from scripts.pen_data import expression_cases

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "benchmark-junctions"
FRESH_SEEDS = (235711, 101317, 192323)
PIXEL_SEED = 67789


def compare_geometry(before, after, cases):
    metrics = {"before": {}, "after": {}}
    outcomes = []
    for index, case in enumerate(cases):
        record = {"index": index, "profile": case["profile"]}
        for stage, segment in (("before", before.segment), ("after", after.segment)):
            segments = segment(case["strokes"])
            ok = len(segments) == len(case["boxes"]) and all(
                iou(item.box, box) >= 0.5 for item, box in zip(segments, case["boxes"], strict=True)
            )
            record[stage] = bool(ok)
            metric = metrics[stage].setdefault(case["profile"], {"correct": 0, "samples": 0})
            metric["samples"] += 1
            metric["correct"] += int(ok)
        if record["before"] and not record["after"]:
            raise ValueError(f"Geometric regression: {case['profile']} case {index}.")
        outcomes.append(record)
    return {"fingerprint": fingerprint({}, cases), "metrics": metrics, "outcomes": outcomes}


def compare_expressions(before, after, cases, expected=None, datasets=None):
    old = evaluate(before, {}, cases)
    if expected is not None and old["expression_records"] != expected["expression_records"]:
        raise ValueError("Previous release no longer reproduces its archived expression outcomes.")
    new = evaluate(after, datasets or {}, cases)
    return {"before": old, "after": new, "paired": paired_outcomes(old, new)}


def main():
    (ROOT / ".cache/benchmarks").mkdir(parents=True, exist_ok=True)
    after = Recognizer()
    before = copy.copy(after)
    before.segment = previous_segmenter(PREVIOUS)
    weights = {}
    for name in ("symbols.joblib", "cnn.pt"):
        content = (ROOT / "models" / name).read_bytes()
        previous = subprocess.check_output(["git", "show", f"{PREVIOUS}:models/{name}"], cwd=ROOT)
        if content != previous:
            raise ValueError("Model weights changed; this audit isolates segmentation.")
        weights[name] = hashlib.sha256(content).hexdigest()
    archived = json.loads(
        subprocess.check_output(
            ["git", "show", f"{PREVIOUS}:models/segmentation_fix.json"], cwd=ROOT
        )
    )
    datasets, original = evaluation_data()
    original_result = compare_expressions(
        before, after, original, archived["original"]["after"], datasets
    )
    for model in ("svm", "cnn"):
        for name in datasets:
            current = json.loads(json.dumps(original_result["after"]["models"][model][name]))
            if current != archived["original"]["after"]["models"][model][name]:
                raise ValueError("Isolated-symbol classification changed.")
    previous_cases = [
        {**case, "seed": seed}
        for seed in archived["protocol"]["fresh_expression_seeds"]
        for case in expression_cases(seed, 600)
    ]
    if fingerprint({}, previous_cases) != archived["protocol"]["fresh_expression_fingerprint"]:
        raise ValueError("Previous expression input fingerprint changed.")
    previous_result = compare_expressions(before, after, previous_cases, archived["fresh"]["after"])
    if not previous_result["after"]["expression_records"][193]["segmentation_ok"]:
        raise ValueError("The recorded 3/64 failure is not fixed.")
    fresh_cases = [
        {**case, "seed": seed} for seed in FRESH_SEEDS for case in expression_cases(seed, 600)
    ]
    fresh_result = compare_expressions(before, after, fresh_cases)
    old_controls = compare_geometry(before, after, list(junction_cases(515151)))
    fresh_controls = compare_geometry(before, after, list(pixel_gap_cases(PIXEL_SEED)))
    report = {
        "protocol": {
            "previous_revision": PREVIOUS,
            "model_sha256": weights,
            "fresh_expression_seeds": FRESH_SEEDS,
            "expressions_per_seed": 600,
            "fresh_expression_fingerprint": fingerprint({}, fresh_cases),
            "pixel_control_seed": PIXEL_SEED,
            "selection_policy": (
                "Developed on recorded case 193 and explicit subpixel unit tests; "
                "fresh seeds evaluated only after freezing the continuous-coordinate guard."
            ),
            "limitations": "New cases are synthetic; no human-operator validation claim.",
        },
        "original": original_result,
        "previous_holdout": previous_result,
        "fresh": fresh_result,
        "previous_junction_controls": old_controls,
        "fresh_pixel_controls": fresh_controls,
    }
    path = ROOT / ".cache/benchmarks/pixel_gap_fix.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for corpus in ("original", "previous_holdout", "fresh"):
        result = report[corpus]
        print(corpus, flush=True)
        for stage in ("before", "after"):
            print(
                stage,
                result[stage]["segmentation"]["all"],
                {
                    m: result[stage]["models"][m]["expressions_all"]["correct"]
                    for m in ("svm", "cnn")
                },
                flush=True,
            )
    for corpus in ("previous_junction_controls", "fresh_pixel_controls"):
        print(corpus, report[corpus]["metrics"], flush=True)
    print("Paired regression and character-error guards passed; report:", path, flush=True)


if __name__ == "__main__":
    main()
