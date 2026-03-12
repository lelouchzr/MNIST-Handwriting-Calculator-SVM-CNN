"""Train a small original CNN on exactly the same input pool as the SVM."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.metrics import accuracy_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from training_data import prepare_data

from inkcalc.cnn import CNNClassifier, SymbolCNN
from inkcalc.features import features_from_pixels

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=20000)
    parser.add_argument("--epochs", type=int, default=8)
    args = parser.parse_args()
    if not 1000 <= args.digits <= 60000 or not 1 <= args.epochs <= 50:
        parser.error("Use 1000–60000 digits and 1–50 epochs.")
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True)
    pixels, labels, test, test_y, metadata = prepare_data(args.digits)
    svm_bundle = joblib.load(ROOT / "models" / "symbols.joblib")
    svm_metadata = svm_bundle["metadata"]
    matched = all(
        metadata[key] == svm_metadata.get(key)
        for key in ("training_inputs_sha256", "evaluation_inputs_sha256")
    )
    if not matched:
        raise ValueError(
            "SVM data hashes differ. Retrain the SVM with the same --digits "
            "before training the CNN."
        )
    classes = np.unique(labels)
    targets = np.searchsorted(classes, labels)
    dataset = TensorDataset(torch.from_numpy(pixels).unsqueeze(1), torch.from_numpy(targets))
    loader = DataLoader(
        dataset,
        batch_size=128,
        shuffle=True,
        generator=torch.Generator().manual_seed(42),
        num_workers=0,
    )
    model = SymbolCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    # Epoch count is fixed in advance; held-out tests are used only after training.
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        correct = 0
        for images, expected in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, expected)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(images)
            correct += int((logits.argmax(1) == expected).sum())
        print(
            f"Epoch {epoch + 1}/{args.epochs}: loss={total_loss / len(dataset):.4f}, "
            f"training accuracy={correct / len(dataset):.4%}",
            flush=True,
        )
    model.eval()
    metadata.update(
        {
            "name": "MNIST + synthetic operators / two-convolution CNN",
            "architecture": "Conv(1,12,3)-ReLU-Pool-Conv(12,24,3)-ReLU-Pool-FC64-FC16",
            "epochs": args.epochs,
            "batch_size": 128,
            "optimizer": "Adam lr=0.001",
            "device": "cpu",
            "torch_version": str(torch.__version__),
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "score_kind": "uncalibrated_softmax",
        }
    )
    output = ROOT / "models"
    output.mkdir(exist_ok=True)
    checkpoint = {"weights": model.state_dict(), "classes": classes.tolist(), "metadata": metadata}
    torch.save(checkpoint, output / "cnn.pt")
    cnn = CNNClassifier()
    cnn_predictions = classes[cnn.predict_proba(test).argmax(1)]
    metadata.update(
        {
            "mnist_test_accuracy": float(accuracy_score(test_y[:2000], cnn_predictions[:2000])),
            "synthetic_operator_test_accuracy": float(
                accuracy_score(test_y[2000:], cnn_predictions[2000:])
            ),
        }
    )
    torch.save(checkpoint, output / "cnn.pt")
    (output / "cnn_metrics.json").write_text(json.dumps(metadata, indent=2) + "\n")
    svm = svm_bundle["model"]
    svm_predictions = svm.predict(np.asarray([features_from_pixels(image) for image in test]))
    comparison = {
        "same_training_inputs": True,
        "same_evaluation_inputs": True,
        "training_inputs_sha256": metadata["training_inputs_sha256"],
        "evaluation_inputs_sha256": metadata["evaluation_inputs_sha256"],
        "digit_test_samples": 2000,
        "synthetic_operator_test_samples": 600,
        "svm": {
            key: svm_metadata[key]
            for key in ("mnist_test_accuracy", "synthetic_operator_test_accuracy", "score_kind")
        },
        "cnn": {
            key: metadata[key]
            for key in ("mnist_test_accuracy", "synthetic_operator_test_accuracy", "score_kind")
        },
        "digit_prediction_agreement": float(
            np.mean(svm_predictions[:2000] == cnn_predictions[:2000])
        ),
        "synthetic_operator_prediction_agreement": float(
            np.mean(svm_predictions[2000:] == cnn_predictions[2000:])
        ),
        "limitations": (
            "Scores use different calibration; synthetic operators do not "
            "validate human handwriting."
        ),
    }
    (output / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print(json.dumps(comparison, indent=2), flush=True)


if __name__ == "__main__":
    main()
