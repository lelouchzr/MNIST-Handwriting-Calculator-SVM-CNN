"""A small convolutional classifier with bounded CPU-only inference."""

import os
from pathlib import Path

import numpy as np
import torch
from torch import nn

CNN_PATH = Path(__file__).resolve().parents[2] / "models" / "cnn.pt"
torch.set_num_threads(min(4, os.cpu_count() or 1))


class SymbolCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(1, 12, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(12, 24, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(24 * 7 * 7, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 16),
        )

    def forward(self, pixels):
        return self.layers(pixels)


class CNNClassifier:
    def __init__(self, path: Path = CNN_PATH):
        if not path.is_file():
            raise FileNotFoundError("CNN missing. Run: uv run python scripts/train_cnn.py")
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        self.model = SymbolCNN()
        self.model.load_state_dict(checkpoint["weights"], strict=True)
        if any(not torch.isfinite(weight).all() for weight in self.model.state_dict().values()):
            raise ValueError("CNN checkpoint contains non-finite weights.")
        self.model.eval()
        self.classes_ = np.asarray(checkpoint["classes"])
        if set(self.classes_) != set("0123456789+-*/()") or len(self.classes_) != 16:
            raise ValueError("CNN checkpoint must contain the 16 supported classes.")
        self.metadata = checkpoint["metadata"]

    def predict_proba(self, pixels) -> np.ndarray:
        values = np.asarray(pixels, dtype=np.float32)
        if values.ndim != 3 or values.shape[1:] != (28, 28):
            raise ValueError("CNN input must have shape (batch, 28, 28).")
        if not np.isfinite(values).all():
            raise ValueError("CNN input must contain finite pixel values.")
        if not len(values):
            return np.empty((0, 16))
        batches = []
        with torch.inference_mode():
            for start in range(0, len(values), 64):
                batch = torch.from_numpy(
                    np.ascontiguousarray(values[start : start + 64])
                ).unsqueeze(1)
                batches.append(torch.softmax(self.model(batch), dim=1).numpy())
        return np.concatenate(batches).astype(np.float64)
