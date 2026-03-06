"""Train a reproducible MNIST + generated-operator classifier (no upstream weights)."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlretrieve

import joblib
import numpy as np
from PIL import Image, ImageDraw
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score
from sklearn.svm import LinearSVC

from inkcalc.features import features

ROOT = Path(__file__).resolve().parents[1]
MNIST_URL = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz"
MNIST_SHA256 = "731c5ac602752760c8e48fbffcf8c3b850d9dc2a2aedcf2cc48468fc17b673d1"
SYMBOLS = ["+", "-", "*", "/", "(", ")"]


def operator_image(symbol: str, rng: np.random.Generator) -> Image.Image:
    image = Image.new("L", (96, 96))
    draw = ImageDraw.Draw(image)
    x0, x1 = int(rng.integers(16, 30)), int(rng.integers(67, 81))
    y0, y1 = int(rng.integers(14, 29)), int(rng.integers(68, 82))
    cx, cy, width = (x0 + x1) // 2, (y0 + y1) // 2, int(rng.integers(4, 10))
    if symbol in {"+", "-", "/"}:
        draw.line([(x0, cy), (x1, cy + int(rng.integers(-4, 5)))], fill=255, width=width)
        if symbol == "+":
            draw.line([(cx, y0), (cx + int(rng.integers(-3, 4)), y1)], fill=255, width=width)
        elif symbol == "/":
            if rng.random() < 0.5:
                image = Image.new("L", (96, 96))
                ImageDraw.Draw(image).line([(x0 + 6, y1), (x1 - 6, y0)], fill=255, width=width)
            else:
                for y in [y0, y1]:
                    draw.ellipse(
                        (cx - width // 2, y - width // 2, cx + width // 2, y + width // 2), fill=255
                    )
    elif symbol == "*":
        draw.line([(x0, y0), (x1, y1)], fill=255, width=width)
        draw.line([(x1, y0), (x0, y1)], fill=255, width=width)
    else:
        angles = np.linspace(-1.15, 1.15, 28)
        direction = -1 if symbol == "(" else 1
        points = [
            (cx + direction * (x1 - x0) * 0.5 * np.cos(a), cy + (y1 - y0) * 0.55 * np.sin(a))
            for a in angles
        ]
        draw.line(points, fill=255, width=width, joint="curve")
    return image.rotate(float(rng.uniform(-12, 12)), Image.Resampling.BILINEAR)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=20000)
    args = parser.parse_args()
    if not 1000 <= args.digits <= 60000:
        parser.error("--digits must be between 1000 and 60000")
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    dataset = cache / "mnist.npz"
    if not dataset.exists():
        print("Downloading MNIST…", flush=True)
        temporary = dataset.with_suffix(".part")
        try:
            urlretrieve(MNIST_URL, temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != MNIST_SHA256:
                raise ValueError("MNIST checksum mismatch; refusing to train on altered data.")
            temporary.replace(dataset)
        finally:
            temporary.unlink(missing_ok=True)
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != MNIST_SHA256:
        raise ValueError("Cached MNIST checksum mismatch. Remove .cache/mnist.npz and retry.")
    rng = np.random.default_rng(42)
    with np.load(dataset, allow_pickle=False) as data:
        indices = rng.permutation(len(data["x_train"]))[: args.digits]
        print(f"Extracting features from {args.digits} MNIST digits…", flush=True)
        x = [features(Image.fromarray(img)) for img in data["x_train"][indices]]
        y = [str(label) for label in data["y_train"][indices]]
        x_test = [features(Image.fromarray(img)) for img in data["x_test"][:2000]]
        y_test = [str(label) for label in data["y_test"][:2000]]
    for symbol in SYMBOLS:
        for _ in range(650):
            x.append(features(operator_image(symbol, rng)))
            y.append(symbol)
    print("Fitting calibrated linear SVM…", flush=True)
    model = CalibratedClassifierCV(LinearSVC(C=2, dual="auto", random_state=42), cv=3)
    model.fit(np.asarray(x), y)
    digit_accuracy = float(accuracy_score(y_test, model.predict(x_test)))
    synthetic_x, synthetic_y = [], []
    for symbol in SYMBOLS:
        for _ in range(100):
            synthetic_x.append(features(operator_image(symbol, rng)))
            synthetic_y.append(symbol)
    operator_accuracy = float(accuracy_score(synthetic_y, model.predict(synthetic_x)))
    metadata = {
        "name": "MNIST + synthetic operators / HOG + calibrated linear SVM",
        "seed": 42,
        "mnist_train_samples": args.digits,
        "mnist_test_samples": 2000,
        "mnist_test_accuracy": digit_accuracy,
        "synthetic_operator_train_samples": 3900,
        "synthetic_operator_test_samples": 600,
        "synthetic_operator_test_accuracy": operator_accuracy,
        "mnist_source": MNIST_URL,
        "mnist_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "limitations": "Synthetic operator tests are not real handwriting validation.",
    }
    output = ROOT / "models"
    output.mkdir(exist_ok=True)
    joblib.dump({"model": model, "metadata": metadata}, output / "symbols.joblib", compress=3)
    (output / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    main()
