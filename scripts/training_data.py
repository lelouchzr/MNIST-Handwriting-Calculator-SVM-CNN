"""Shared, checksum-verified training and held-out evaluation inputs."""

import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
from pen_data import render, symbol_strokes
from PIL import Image, ImageDraw
from scipy.ndimage import affine_transform, maximum_filter

from inkcalc.features import normalize
from inkcalc.segmentation import rasterize

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


@dataclass
class TrainingData:
    pixels: np.ndarray
    labels: np.ndarray
    groups: np.ndarray
    validation: np.ndarray
    validation_labels: np.ndarray
    metadata: dict


def augment(pixels, rng):
    """Mild affine/thickness noise; variants retain their source calibration group."""
    angle = rng.uniform(-0.16, 0.16)
    transform = np.array(
        [[np.cos(angle), -np.sin(angle) + rng.uniform(-0.10, 0.10)], [np.sin(angle), np.cos(angle)]]
    )
    transform *= rng.uniform(0.94, 1.06)
    inverse = np.linalg.inv(transform)
    center = np.array([13.5, 13.5])
    offset = center - inverse @ center + rng.uniform(-0.65, 0.65, 2)
    result = affine_transform(pixels, inverse, offset=offset, order=1, mode="constant")
    if rng.random() < 0.15:
        result = maximum_filter(result, size=2)
    return np.clip(result, 0, 1).astype(np.float32)


def prepare_data(digits=40000):
    if not 1000 <= digits <= 55000:
        raise ValueError("Use 1000–55000 training digits; reserve 5000 for validation.")
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    dataset = cache / "mnist.npz"
    if not dataset.exists():
        temporary = dataset.with_suffix(".part")
        try:
            urlretrieve(MNIST_URL, temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != MNIST_SHA256:
                raise ValueError("MNIST checksum mismatch.")
            temporary.replace(dataset)
        finally:
            temporary.unlink(missing_ok=True)
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != MNIST_SHA256:
        raise ValueError("Cached MNIST checksum mismatch.")
    recipe = hashlib.sha256(
        Path(__file__).read_bytes()
        + (ROOT / "scripts/pen_data.py").read_bytes()
        + (ROOT / "src/inkcalc/features.py").read_bytes()
        + inspect.getsource(rasterize).encode()
    ).hexdigest()
    saved = cache / f"training-{digits}-{recipe[:12]}.npz"
    if saved.exists():
        with np.load(saved, allow_pickle=False) as data:
            return TrainingData(
                data["pixels"],
                data["labels"],
                data["groups"],
                data["validation"],
                data["validation_labels"],
                json.loads(str(data["metadata"])),
            )
    rng = np.random.default_rng(42)
    with np.load(dataset, allow_pickle=False) as data:
        order = rng.permutation(len(data["x_train"]))
        images = data["x_train"][order[:digits]]
        labels = data["y_train"][order[:digits]].astype(str)
        validation_images = data["x_train"][order[digits : digits + 5000]]
        validation_labels = data["y_train"][order[digits : digits + 5000]].astype(str).tolist()
    print(f"Preparing {digits} MNIST originals + affine variants…", flush=True)
    originals = [normalize(Image.fromarray(image)) for image in images]
    pixels = originals + [augment(image, rng) for image in originals]
    targets = labels.tolist() * 2
    groups = list(range(digits)) * 2
    for symbol in SYMBOLS:
        for index in range(1200):
            image = (
                operator_image(symbol, rng)
                if index < 600
                else render(symbol_strokes(symbol, rng), rng.uniform(4, 9))
            )
            pixels.append(normalize(image))
            targets.append(symbol)
            groups.append(digits + len(groups) - 2 * digits)
    for symbol in "0123456789":
        for _ in range(450):
            pixels.append(normalize(render(symbol_strokes(symbol, rng), rng.uniform(4, 9))))
            targets.append(symbol)
            groups.append(digits + len(groups) - 2 * digits)
    validation = [normalize(Image.fromarray(image)) for image in validation_images]
    validation_rng = np.random.default_rng(7301)
    for symbol in list("0123456789") + SYMBOLS:
        for index in range(30 if symbol.isdigit() else 100):
            image = (
                operator_image(symbol, validation_rng)
                if not symbol.isdigit() and index < 50
                else render(symbol_strokes(symbol, validation_rng), validation_rng.uniform(4, 9))
            )
            validation.append(normalize(image))
            validation_labels.append(symbol)
    pixels, targets = np.asarray(pixels, dtype=np.float32), np.asarray(targets)
    validation = np.asarray(validation, dtype=np.float32)
    validation_labels = np.asarray(validation_labels)
    metadata = {
        "seed": 42,
        "recipe_version": "affine-pen-v2",
        "mnist_train_samples": digits,
        "mnist_augmented_samples": digits,
        "pen_digit_train_samples": 4500,
        "synthetic_operator_train_samples": 7200,
        "training_samples": len(pixels),
        "validation_samples": len(validation),
        "validation_mnist_samples": 5000,
        "validation_seed": 7301,
        "mnist_source": MNIST_URL,
        "mnist_sha256": MNIST_SHA256,
        "training_inputs_sha256": hashlib.sha256(
            pixels.tobytes() + "|".join(targets).encode()
        ).hexdigest(),
        "validation_inputs_sha256": hashlib.sha256(
            validation.tobytes() + "|".join(validation_labels).encode()
        ).hexdigest(),
        "augmentation": (
            "affine ±9 degrees, shear ±0.10, scale 0.94–1.06, shift ±0.65px; 15% dilation"
        ),
        "limitations": "Procedural pen samples share a generator family; not human validation.",
    }
    np.savez_compressed(
        saved,
        pixels=pixels,
        labels=targets,
        groups=np.asarray(groups),
        validation=validation,
        validation_labels=validation_labels,
        metadata=json.dumps(metadata),
    )
    return TrainingData(
        pixels, targets, np.asarray(groups), validation, validation_labels, metadata
    )
