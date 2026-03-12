"""Train the calibrated SVM on the shared normalized dataset."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score
from sklearn.svm import LinearSVC
from training_data import prepare_data

from inkcalc.features import features_from_pixels

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=20000)
    args = parser.parse_args()
    if not 1000 <= args.digits <= 60000:
        parser.error("--digits must be between 1000 and 60000")
    pixels, y, test, test_y, metadata = prepare_data(args.digits)
    x = np.asarray([features_from_pixels(image) for image in pixels])
    test_x = np.asarray([features_from_pixels(image) for image in test])
    print("Fitting calibrated linear SVM…", flush=True)
    model = CalibratedClassifierCV(LinearSVC(C=2, dual="auto", random_state=42), cv=3)
    model.fit(x, y)
    predictions = model.predict(test_x)
    metadata.update(
        {
            "name": "MNIST + synthetic operators / HOG + calibrated linear SVM",
            "score_kind": "calibrated_probability",
            "mnist_test_accuracy": float(accuracy_score(test_y[:2000], predictions[:2000])),
            "synthetic_operator_test_accuracy": float(
                accuracy_score(test_y[2000:], predictions[2000:])
            ),
        }
    )
    output = ROOT / "models"
    output.mkdir(exist_ok=True)
    joblib.dump({"model": model, "metadata": metadata}, output / "symbols.joblib", compress=3)
    (output / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    main()
