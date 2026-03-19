"""Train the calibrated SVM on the shared normalized dataset."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.svm import LinearSVC
from training_data import prepare_data

from inkcalc.features import features_from_pixels

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=40000)
    args = parser.parse_args()
    if not 1000 <= args.digits <= 55000:
        parser.error("--digits must be between 1000 and 55000")
    data = prepare_data(args.digits)
    metadata = data.metadata.copy()
    x = np.asarray([features_from_pixels(image) for image in data.pixels])
    validation_x = np.asarray([features_from_pixels(image) for image in data.validation])
    folds = list(
        StratifiedGroupKFold(3, shuffle=True, random_state=42).split(x, data.labels, data.groups)
    )
    print("Fitting source-group-calibrated linear SVM…", flush=True)
    model = CalibratedClassifierCV(LinearSVC(C=2, dual="auto", random_state=42), cv=folds)
    model.fit(x, data.labels)
    metadata.update(
        {
            "name": "Augmented MNIST + procedural pen paths / HOG + calibrated linear SVM",
            "score_kind": "calibrated_probability",
            "calibration": "3 sigmoid folds, original and augmented source groups kept together",
            "validation_accuracy": float(
                accuracy_score(data.validation_labels, model.predict(validation_x))
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
