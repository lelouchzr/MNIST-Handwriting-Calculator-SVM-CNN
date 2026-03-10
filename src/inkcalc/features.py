"""The same image transform is used during training and inference."""

import numpy as np
from PIL import Image
from scipy.ndimage import center_of_mass, shift
from skimage.feature import hog


def normalize(image: Image.Image) -> np.ndarray:
    array = np.asarray(image.convert("L"))
    ys, xs = np.where(array > 30)
    if len(xs) == 0:
        return np.zeros((28, 28), dtype=np.float32)
    crop = Image.fromarray(array[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1])
    crop.thumbnail((20, 20), Image.Resampling.LANCZOS)
    # thumbnail never enlarges; small uploaded digits still need the MNIST scale.
    scale = min(20 / crop.width, 20 / crop.height)
    crop = crop.resize(
        (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
        Image.Resampling.LANCZOS,
    )
    frame = Image.new("L", (28, 28))
    frame.paste(crop, ((28 - crop.width) // 2, (28 - crop.height) // 2))
    pixels = np.asarray(frame, dtype=np.float32) / 255
    cy, cx = center_of_mass(pixels)
    return shift(pixels, (13.5 - cy, 13.5 - cx), order=1, mode="constant")


def features(image: Image.Image) -> np.ndarray:
    return features_from_pixels(normalize(image))


def features_from_pixels(pixels: np.ndarray) -> np.ndarray:
    """Extract HOG without recropping or recentering an already normalized input."""
    return hog(
        pixels,
        orientations=9,
        pixels_per_cell=(7, 7),
        cells_per_block=(2, 2),
        block_norm="L2-Hys",
    ).astype(np.float32)
