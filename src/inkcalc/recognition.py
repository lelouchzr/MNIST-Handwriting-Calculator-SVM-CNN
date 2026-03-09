"""Group pen strokes into symbols and classify normalized raster crops."""

import base64
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw

from inkcalc.features import features

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "symbols.joblib"
DISPLAY = {"*": "×", "/": "÷", "-": "−"}


class Recognizer:
    def __init__(self, path: Path = MODEL_PATH):
        if not path.is_file():
            raise FileNotFoundError("Model missing. Run: uv run python scripts/train.py")
        # Only load the repository's trusted artifact; never accept pickle uploads.
        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.metadata = bundle["metadata"]

    def recognize(self, strokes: list[list[tuple[float, float]]]) -> list[dict]:
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
        predictions = []
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
            if max(right - left, bottom - top) < 12:
                alternatives = [{"label": ".", "confidence": 1.0}]
            else:
                probabilities = self.model.predict_proba([features(image)])[0]
                order = np.argsort(probabilities)[::-1][:3]
                alternatives = [
                    {
                        "label": DISPLAY.get(
                            str(self.model.classes_[i]), str(self.model.classes_[i])
                        ),
                        "confidence": round(float(probabilities[i]), 4),
                    }
                    for i in order
                ]
            thumbnail = image.copy()
            thumbnail.thumbnail((64, 64))
            output = BytesIO()
            thumbnail.save(output, format="PNG")
            predictions.append(
                {
                    "label": alternatives[0]["label"],
                    "confidence": alternatives[0]["confidence"],
                    "alternatives": alternatives,
                    "box": group["box"],
                    "thumbnail": "data:image/png;base64,"
                    + base64.b64encode(output.getvalue()).decode("ascii"),
                }
            )
        return predictions
