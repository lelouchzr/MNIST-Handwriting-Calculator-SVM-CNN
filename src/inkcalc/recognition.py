"""Group pen strokes into symbols and classify normalized raster crops."""

import base64
import pickle
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw

from inkcalc.cnn import CNN_PATH, CNNClassifier
from inkcalc.explanation import occlusion_sensitivity
from inkcalc.features import features_from_pixels, normalize

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "symbols.joblib"
DISPLAY = {"*": "×", "/": "÷", "-": "−"}


class ModelUnavailableError(ValueError):
    """The requested classifier is missing or could not be loaded."""


@dataclass
class Segment:
    image: Image.Image
    box: list[float]

    @property
    def is_point(self) -> bool:
        left, top, right, bottom = self.box
        return max(right - left, bottom - top) < 12


def png_data(image: Image.Image) -> str:
    output = BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


class Recognizer:
    def __init__(self, path: Path = MODEL_PATH, cnn_path: Path = CNN_PATH):
        self.model = None
        self.cnn = None
        self.metadata = {}
        self.errors = {}
        try:
            # Only load this repository's trusted artifact, never an upload.
            bundle = joblib.load(path)
            self.model = bundle["model"]
            self.metadata = bundle["metadata"]
        except (FileNotFoundError, ValueError, KeyError, EOFError, pickle.UnpicklingError) as exc:
            self.errors["svm"] = str(exc)
        try:
            self.cnn = CNNClassifier(cnn_path)
        except (
            FileNotFoundError,
            ValueError,
            KeyError,
            RuntimeError,
            EOFError,
            pickle.UnpicklingError,
        ) as exc:
            self.errors["cnn"] = str(exc)
        if self.model is None and self.cnn is None:
            raise FileNotFoundError(
                "No recognition model is available. Train the SVM or CNN first."
            )

    @property
    def models_status(self):
        return {
            "svm": {
                "ready": self.model is not None,
                "name": "HOG + SVM",
                "score_kind": "calibrated_probability",
                "metrics": self.metadata,
                "error": self.errors.get("svm"),
            },
            "cnn": {
                "ready": self.cnn is not None,
                "name": "CNN",
                "score_kind": "uncalibrated_softmax",
                "metrics": self.cnn.metadata if self.cnn else {},
                "error": self.errors.get("cnn"),
            },
        }

    def _backend(self, model_id):
        if model_id == "svm" and self.model is not None:
            return self.model, features_from_pixels
        if model_id == "cnn" and self.cnn is not None:
            return self.cnn, lambda pixels: pixels
        if model_id not in {"svm", "cnn"}:
            raise ValueError("Unknown recognition model.")
        raise ModelUnavailableError(f"{model_id.upper()} is unavailable. Train that model first.")

    def _requested(self, model_id):
        requested = ["svm", "cnn"] if model_id == "compare" else [model_id]
        for name in requested:
            self._backend(name)
        return requested

    def _prediction(self, pixels, model_id, is_point):
        estimator, extract = self._backend(model_id)
        score_kind = "calibrated_probability" if model_id == "svm" else "uncalibrated_softmax"
        if is_point:
            probabilities = []
            alternatives = [{"label": ".", "confidence": 1.0}]
        else:
            scores = estimator.predict_proba([extract(pixels)])[0]
            probabilities = [
                {
                    "label": DISPLAY.get(str(estimator.classes_[i]), str(estimator.classes_[i])),
                    "confidence": float(scores[i]),
                }
                for i in np.argsort(scores)[::-1]
            ]
            alternatives = probabilities[:3]
        return {
            "predicted_label": alternatives[0]["label"],
            "confidence": alternatives[0]["confidence"],
            "method": "geometry" if is_point else "classifier",
            "probabilities": probabilities,
            "alternatives": alternatives,
            "model_id": model_id,
            "score_kind": "rule" if is_point else score_kind,
        }

    @staticmethod
    def segment(strokes: list[list[tuple[float, float]]]) -> list[Segment]:
        bounded = []
        for stroke in strokes:
            xs, ys = zip(*stroke, strict=True)
            bounded.append({"points": stroke, "box": [min(xs), min(ys), max(xs), max(ys)]})
        bounded.sort(key=lambda item: item["box"][0])
        groups: list[dict] = []
        for item in bounded:
            box = item["box"]
            # Merge overlapping x-ranges, including disconnected '+' and '÷' strokes.
            if groups and box[0] <= groups[-1]["box"][2] + 7:
                group = groups[-1]
                group["strokes"].append(item["points"])
                group["box"] = [
                    min(group["box"][0], box[0]),
                    min(group["box"][1], box[1]),
                    max(group["box"][2], box[2]),
                    max(group["box"][3], box[3]),
                ]
            else:
                groups.append({"strokes": [item["points"]], "box": box.copy()})
        if len(groups) > 64:
            raise ValueError("Limit the expression to 64 symbols.")
        segments = []
        for group in groups:
            left, top, right, bottom = group["box"]
            image = Image.new("L", (max(1, int(right - left)) + 16, max(1, int(bottom - top)) + 16))
            draw = ImageDraw.Draw(image)
            for stroke in group["strokes"]:
                points = [(x - left + 8, y - top + 8) for x, y in stroke]
                if len(points) == 1:
                    x, y = points[0]
                    draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=255)
                else:
                    draw.line(points, fill=255, width=6, joint="curve")
            segments.append(Segment(image, group["box"]))
        return segments

    def recognize(
        self, strokes: list[list[tuple[float, float]]], model_id: str = "svm"
    ) -> list[dict]:
        requested = self._requested(model_id)
        primary = "svm" if model_id == "compare" else model_id
        predictions = []
        for segment in self.segment(strokes):
            pixels = normalize(segment.image)
            models = {name: self._prediction(pixels, name, segment.is_point) for name in requested}
            prediction = models[primary]
            thumbnail = segment.image.copy()
            thumbnail.thumbnail((64, 64))
            predictions.append(
                {
                    "label": prediction["predicted_label"],
                    **prediction,
                    "models": models,
                    "agreement": (
                        models["svm"]["predicted_label"] == models["cnn"]["predicted_label"]
                    )
                    if model_id == "compare" and not segment.is_point
                    else None,
                    "box": segment.box,
                    "thumbnail": png_data(thumbnail),
                    "input": {
                        "crop": png_data(segment.image),
                        "normalized": png_data(
                            Image.fromarray(np.clip(pixels * 255, 0, 255).round().astype(np.uint8))
                        ),
                        "width": segment.image.width,
                        "height": segment.image.height,
                    },
                }
            )
        return predictions

    def explain(
        self, strokes: list[list[tuple[float, float]]], symbol_index: int, model_id: str = "svm"
    ) -> dict:
        requested = self._requested(model_id)
        segments = self.segment(strokes)
        if not 0 <= symbol_index < len(segments):
            raise ValueError("The selected symbol does not exist in this drawing.")
        segment = segments[symbol_index]
        pixels = normalize(segment.image)
        results = {}
        for name in requested:
            if segment.is_point:
                results[name] = {
                    "supported": False,
                    "model_id": name,
                    "reason": "This decimal point was detected by size, not the classifier. "
                    "No model sensitivity map is available.",
                }
                continue
            estimator, extract = self._backend(name)
            target = int(np.argmax(estimator.predict_proba([extract(pixels)])[0]))
            label = str(estimator.classes_[target])
            results[name] = {
                "label": DISPLAY.get(label, label),
                "model_id": name,
                **occlusion_sensitivity(pixels, estimator, target, feature_fn=extract),
            }
        if model_id == "compare":
            return {
                "models": results,
                "shared_max_abs_change": max(
                    item.get("max_abs_change", 0.0) for item in results.values()
                ),
            }
        return results[model_id]
