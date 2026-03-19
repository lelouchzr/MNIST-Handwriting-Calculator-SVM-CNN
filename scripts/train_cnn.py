"""Train on shared inputs; choose the checkpoint using training-split validation only."""

import argparse
import copy
import json
from pathlib import Path

import joblib
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from training_data import prepare_data

from inkcalc.cnn import SymbolCNN

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=40000)
    parser.add_argument("--epochs", type=int, default=12)
    args = parser.parse_args()
    if not 1000 <= args.digits <= 55000 or not 1 <= args.epochs <= 50:
        parser.error("Use 1000–55000 training digits and 1–50 epochs.")
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True)
    data = prepare_data(args.digits)
    metadata = data.metadata.copy()
    svm_metadata = joblib.load(ROOT / "models/symbols.joblib")["metadata"]
    if any(
        metadata[key] != svm_metadata.get(key)
        for key in ("training_inputs_sha256", "validation_inputs_sha256")
    ):
        raise ValueError("Train the SVM on this exact dataset before training the CNN.")
    classes = np.unique(data.labels)
    targets = np.searchsorted(classes, data.labels)
    validation_targets = np.searchsorted(classes, data.validation_labels)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(data.pixels).unsqueeze(1), torch.from_numpy(targets)),
        batch_size=128,
        shuffle=True,
        generator=torch.Generator().manual_seed(42),
        num_workers=0,
    )
    validation = DataLoader(
        TensorDataset(
            torch.from_numpy(data.validation).unsqueeze(1), torch.from_numpy(validation_targets)
        ),
        batch_size=128,
    )
    model = SymbolCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=8, gamma=0.3)
    criterion = nn.CrossEntropyLoss()
    best_accuracy, best_weights, best_epoch, history = -1, None, 0, []
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for images, expected in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, expected)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(images)
        model.eval()
        correct = 0
        with torch.inference_mode():
            for images, expected in validation:
                correct += int((model(images).argmax(1) == expected).sum())
        accuracy = correct / len(data.validation)
        if accuracy > best_accuracy:
            best_accuracy, best_epoch = accuracy, epoch + 1
            best_weights = copy.deepcopy(model.state_dict())
        history.append(
            {
                "epoch": epoch + 1,
                "loss": total_loss / len(data.labels),
                "validation_accuracy": accuracy,
            }
        )
        print(
            f"Epoch {epoch + 1}/{args.epochs}: loss={history[-1]['loss']:.4f}, "
            f"validation={accuracy:.3%}",
            flush=True,
        )
        scheduler.step()
    metadata.update(
        {
            "name": "Augmented MNIST + procedural pen paths / two-convolution CNN",
            "architecture": "Conv(1,12,3)-ReLU-Pool-Conv(12,24,3)-ReLU-Pool-FC64-FC16",
            "epochs": args.epochs,
            "best_epoch": best_epoch,
            "batch_size": 128,
            "optimizer": "Adam lr=0.001; StepLR step=8 gamma=0.3",
            "device": "cpu",
            "torch_version": str(torch.__version__),
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "score_kind": "uncalibrated_softmax",
            "validation_accuracy": best_accuracy,
            "checkpoint_selection": "highest validation accuracy; final evaluation never used",
        }
    )
    output = ROOT / "models"
    torch.save(
        {"weights": best_weights, "classes": classes.tolist(), "metadata": metadata},
        output / "cnn.pt",
    )
    (output / "cnn_metrics.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "training_history.json").write_text(json.dumps(history, indent=2) + "\n")


if __name__ == "__main__":
    main()
