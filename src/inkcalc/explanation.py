"""Signed occlusion sensitivity on a fixed model input, not causal attribution."""

import numpy as np

from inkcalc.features import features_from_pixels

PATCH_SIZE = 5


def occlusion_sensitivity(pixels: np.ndarray, model, target: int) -> dict:
    baseline = float(model.predict_proba([features_from_pixels(pixels)])[0, target])
    masked_features = []
    positions = []
    for row in range(28 - PATCH_SIZE + 1):
        for column in range(28 - PATCH_SIZE + 1):
            masked = pixels.copy()
            masked[row : row + PATCH_SIZE, column : column + PATCH_SIZE] = 0
            masked_features.append(features_from_pixels(masked))
            positions.append((row, column))

    # One batched prediction; each perturbed image retains the same coordinates.
    scores = model.predict_proba(np.asarray(masked_features))[:, target]
    deltas = baseline - scores
    total = np.zeros((28, 28), dtype=np.float64)
    counts = np.zeros((28, 28), dtype=np.int32)
    for (row, column), delta in zip(positions, deltas, strict=True):
        total[row : row + PATCH_SIZE, column : column + PATCH_SIZE] += delta
        counts[row : row + PATCH_SIZE, column : column + PATCH_SIZE] += 1
    sensitivity = total / counts
    return {
        "supported": True,
        "baseline_confidence": baseline,
        "patch_size": PATCH_SIZE,
        "windows": len(positions),
        "sensitivity": sensitivity.round(7).tolist(),
        "max_abs_change": float(np.max(np.abs(sensitivity))),
        "min_change": float(sensitivity.min()),
        "max_change": float(sensitivity.max()),
    }
