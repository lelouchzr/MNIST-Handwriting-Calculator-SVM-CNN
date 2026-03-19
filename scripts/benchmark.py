"""Paired, deterministic before/after evaluation. Never used to select checkpoints."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
from pen_data import SYMBOLS, expression_cases, render, symbol_strokes
from PIL import Image
from sklearn.metrics import accuracy_score

from inkcalc.features import normalize
from inkcalc.recognition import Recognizer

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "200719072ee4fc0463abc31b89973fa0fb80c6b2"
SEED = 90210


def baseline_recognizer():
    directory = ROOT / ".cache" / "baseline-v1"
    directory.mkdir(parents=True, exist_ok=True)
    for source, name in [
        ("src/inkcalc/recognition.py", "recognition.py"),
        ("models/symbols.joblib", "symbols.joblib"),
        ("models/cnn.pt", "cnn.pt"),
    ]:
        content = subprocess.check_output(["git", "show", f"{BASELINE}:{source}"], cwd=ROOT)
        (directory / name).write_bytes(content)
    spec = importlib.util.spec_from_file_location("inkcalc_baseline", directory / "recognition.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.Recognizer(directory / "symbols.joblib", directory / "cnn.pt")


def evaluation_data():
    from training_data import MNIST_SHA256

    archive = ROOT / ".cache/mnist.npz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != MNIST_SHA256:
        raise ValueError("MNIST archive checksum mismatch.")
    cache = ROOT / ".cache/algorithm-evaluation.npz"
    if not cache.exists():
        with np.load(archive, allow_pickle=False) as data:
            images = np.asarray(
                [normalize(Image.fromarray(x)) for x in data["x_test"]], dtype=np.float32
            )
            labels = data["y_test"].astype(str)
        rng = np.random.default_rng(SEED)
        pen_x, pen_y = [], []
        for label in list("0123456789") + SYMBOLS:
            for _ in range(100 if label.isdigit() else 200):
                pen_x.append(normalize(render(symbol_strokes(label, rng), rng.uniform(4, 8))))
                pen_y.append(label)
        np.savez_compressed(
            cache, mnist=images, mnist_y=labels, pen=np.asarray(pen_x), pen_y=np.asarray(pen_y)
        )
    with np.load(cache, allow_pickle=False) as data:
        datasets = {
            "mnist_digits": (data["mnist"], data["mnist_y"]),
            "pen_digits": (data["pen"][:1000], data["pen_y"][:1000]),
            "pen_operators": (data["pen"][1000:], data["pen_y"][1000:]),
        }
    return datasets, list(expression_cases(SEED, 240))


def fingerprint(datasets, cases):
    digest = hashlib.sha256()
    for images, labels in datasets.values():
        digest.update(images.tobytes())
        digest.update("|".join(labels).encode())
    digest.update(json.dumps(cases, sort_keys=True, separators=(",", ":")).encode())
    return digest.hexdigest()


def canonical(label):
    return label.replace("×", "*").replace("÷", "/").replace("−", "-")


def iou(a, b):
    # Expand centerline bounds to make point/line areas nonzero.
    a, b = np.asarray(a) + [-3, -3, 3, 3], np.asarray(b) + [-3, -3, 3, 3]
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1])
    return intersection / max(1, area - intersection)


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        next_row = [i]
        for j, right in enumerate(b, 1):
            next_row.append(min(row[j] + 1, next_row[-1] + 1, row[j - 1] + (left != right)))
        row = next_row
    return row[-1]


def evaluate(recognizer, datasets, cases):
    results = {"svm": {}, "cnn": {}}
    for model_id in results:
        estimator, extract = recognizer._backend(model_id)
        for name, (pixels, expected) in datasets.items():
            features = np.asarray([extract(image) for image in pixels])
            predicted = estimator.classes_[estimator.predict_proba(features).argmax(1)]
            wrong = {}
            for left, right in zip(expected, predicted, strict=True):
                if left != right:
                    pair = f"{left} -> {right}"
                    wrong[pair] = wrong.get(pair, 0) + 1
            results[model_id][name] = {
                "samples": len(expected),
                "accuracy": float(accuracy_score(expected, predicted)),
                "correct": int(np.sum(expected == predicted)),
                "top_confusions": sorted(wrong.items(), key=lambda x: (-x[1], x[0]))[:12],
            }
            print(f"{model_id} {name}: {results[model_id][name]['accuracy']:.3%}", flush=True)
    records = []
    for case in cases:
        segments = recognizer.segment(case["strokes"])
        segmentation_ok = len(segments) == len(case["boxes"]) and all(
            iou(segment.box, box) >= 0.5
            for segment, box in zip(segments, case["boxes"], strict=True)
        )
        predictions = {}
        tokens = recognizer.recognize(case["strokes"], "compare")
        for model_id in results:
            predictions[model_id] = "".join(
                canonical(token["models"][model_id]["predicted_label"]) for token in tokens
            )
        records.append(
            {
                "profile": case["profile"],
                "expected": case["expression"],
                "segmentation_ok": bool(segmentation_ok),
                "predictions": predictions,
            }
        )
    for model_id in results:
        for profile in ["all"] + sorted({case["profile"] for case in cases}):
            subset = [r for r in records if profile == "all" or r["profile"] == profile]
            exact = sum(r["predictions"][model_id] == r["expected"] for r in subset)
            chars = sum(len(r["expected"]) for r in subset)
            edits = sum(distance(r["expected"], r["predictions"][model_id]) for r in subset)
            results[model_id][f"expressions_{profile}"] = {
                "samples": len(subset),
                "correct": exact,
                "accuracy": exact / len(subset),
                "character_error_rate": edits / chars,
            }
    segmentation = {}
    for profile in ["all"] + sorted({case["profile"] for case in cases}):
        subset = [r for r in records if profile == "all" or r["profile"] == profile]
        count = sum(r["segmentation_ok"] for r in subset)
        segmentation[profile] = {
            "correct": count,
            "samples": len(subset),
            "accuracy": count / len(subset),
        }
    return {"models": results, "segmentation": segmentation, "expression_records": records}


def publish_metrics(result, before):
    """Update artifact metadata only after the frozen final evaluation has finished."""
    output = ROOT / "models"
    evaluation_hash = result["protocol"]["fingerprint"]
    svm = joblib.load(output / "symbols.joblib")
    cnn = torch.load(output / "cnn.pt", map_location="cpu", weights_only=True)
    for key in ("training_inputs_sha256", "validation_inputs_sha256"):
        if svm["metadata"][key] != cnn["metadata"][key]:
            raise ValueError("The two models do not share the same training/validation inputs.")
    for model, bundle, metrics_name in [
        ("svm", svm, "metrics.json"),
        ("cnn", cnn, "cnn_metrics.json"),
    ]:
        meta = bundle["metadata"]
        meta.pop("recipe_sha256", None)
        meta.update(
            {
                "recipe_version": "affine-pen-v2",
                "evaluation_inputs_sha256": evaluation_hash,
                "mnist_test_samples": 10000,
                "synthetic_operator_test_samples": 1200,
                "mnist_test_accuracy": result["models"][model]["mnist_digits"]["accuracy"],
                "synthetic_operator_test_accuracy": result["models"][model]["pen_operators"][
                    "accuracy"
                ],
                "pen_digit_test_accuracy": result["models"][model]["pen_digits"]["accuracy"],
            }
        )
        (output / metrics_name).write_text(json.dumps(meta, indent=2) + "\n")
    joblib.dump(svm, output / "symbols.joblib", compress=3)
    torch.save(cnn, output / "cnn.pt")
    comparison = {
        "same_training_inputs": True,
        "same_evaluation_inputs": True,
        "training_inputs_sha256": svm["metadata"]["training_inputs_sha256"],
        "validation_inputs_sha256": svm["metadata"]["validation_inputs_sha256"],
        "evaluation_inputs_sha256": evaluation_hash,
        "digit_test_samples": 10000,
        "synthetic_operator_test_samples": 1200,
        "svm": {
            key: svm["metadata"][key]
            for key in ("mnist_test_accuracy", "synthetic_operator_test_accuracy", "score_kind")
        },
        "cnn": {
            key: cnn["metadata"][key]
            for key in ("mnist_test_accuracy", "synthetic_operator_test_accuracy", "score_kind")
        },
        "limitations": result["protocol"]["limitations"],
    }
    (output / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    summary = {
        "protocol": result["protocol"],
        "models": {},
        "segmentation": {"before": before["segmentation"], "after": result["segmentation"]},
    }
    for model in ("svm", "cnn"):
        summary["models"][model] = {}
        for name, after_metric in result["models"][model].items():
            old = before["models"][model][name]
            summary["models"][model][name] = {
                "samples": after_metric["samples"],
                "before": old["accuracy"],
                "after": after_metric["accuracy"],
                "delta_percentage_points": 100 * (after_metric["accuracy"] - old["accuracy"]),
            }
    (output / "algorithm_comparison.json").write_text(json.dumps(summary, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["before", "after"], required=True)
    args = parser.parse_args()
    datasets, cases = evaluation_data()
    stamp = fingerprint(datasets, cases)
    protocol = {
        "seed": SEED,
        "fingerprint": stamp,
        "baseline_revision": BASELINE,
        "segmentation_match": "ordered count and per-box IoU >= 0.5, bounds padded 3px",
        "limitations": "Pen digits/operators/expressions are synthetic, not human validation.",
        "test_policy": "Fixed final evaluation; not used for checkpoint selection.",
    }
    output = ROOT / "models" / f"algorithm_{args.stage}.json"
    if args.stage == "after":
        before = json.loads((ROOT / "models/algorithm_before.json").read_text())
        if before["protocol"] != protocol:
            raise ValueError(
                "Evaluation protocol changed; regenerate the baseline with original code."
            )
    recognizer = baseline_recognizer() if args.stage == "before" else Recognizer()
    result = {"protocol": protocol, **evaluate(recognizer, datasets, cases)}
    output.write_text(json.dumps(result, indent=2) + "\n")
    if args.stage == "after":
        publish_metrics(result, before)
    print(
        json.dumps(
            {
                "segmentation": result["segmentation"],
                "expressions": {m: v["expressions_all"] for m, v in result["models"].items()},
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
