"""Group pen strokes into symbols and classify normalized raster crops."""

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw

from inkcalc.explanation import occlusion_sensitivity
from inkcalc.features import features_from_pixels, normalize

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "symbols.joblib"
DISPLAY = {"*": "×", "/": "÷", "-": "−"}


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
    def __init__(self, path: Path = MODEL_PATH):
        if not path.is_file():
            raise FileNotFoundError("Model missing. Run: uv run python scripts/train.py")
        # Only load the repository's trusted artifact; never accept pickle uploads.
        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.metadata = bundle["metadata"]

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

    def recognize(self, strokes: list[list[tuple[float, float]]]) -> list[dict]:
        predictions = []
        for segment in self.segment(strokes):
            pixels = normalize(segment.image)
            if segment.is_point:
                probabilities = []
                alternatives = [{"label": ".", "confidence": 1.0}]
            else:
                scores = self.model.predict_proba([features_from_pixels(pixels)])[0]
                order = np.argsort(scores)[::-1]
                probabilities = [
                    {
                        "label": DISPLAY.get(
                            str(self.model.classes_[i]), str(self.model.classes_[i])
                        ),
                        "confidence": float(scores[i]),
                    }
                    for i in order
                ]
                alternatives = probabilities[:3]
            thumbnail = segment.image.copy()
            thumbnail.thumbnail((64, 64))
            predictions.append(
                {
                    "label": alternatives[0]["label"],
                    "predicted_label": alternatives[0]["label"],
                    "confidence": alternatives[0]["confidence"],
                    "method": "geometry" if segment.is_point else "classifier",
                    "alternatives": alternatives,
                    "probabilities": probabilities,
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

    def explain(self, strokes: list[list[tuple[float, float]]], symbol_index: int) -> dict:
        segments = self.segment(strokes)
        if not 0 <= symbol_index < len(segments):
            raise ValueError("The selected symbol does not exist in this drawing.")
        segment = segments[symbol_index]
        if segment.is_point:
            return {
                "supported": False,
                "reason": "This decimal point was detected by size, "
                "not the classifier. No model sensitivity map is available.",
            }
        pixels = normalize(segment.image)
        scores = self.model.predict_proba([features_from_pixels(pixels)])[0]
        target = int(np.argmax(scores))
        label = str(self.model.classes_[target])
        return {
            "label": DISPLAY.get(label, label),
            **occlusion_sensitivity(pixels, self.model, target),
        }
