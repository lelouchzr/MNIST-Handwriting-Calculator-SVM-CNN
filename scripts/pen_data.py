"""Original procedural pen paths; synthetic evidence, not a human-writing benchmark."""

import numpy as np

from inkcalc.segmentation import rasterize

SYMBOLS = ["+", "-", "*", "/", "(", ")"]


def arc(cx, cy, rx, ry, start, stop, count=30):
    angles = np.linspace(start, stop, count)
    return np.column_stack([cx + rx * np.cos(angles), cy + ry * np.sin(angles)]).tolist()


def symbol_strokes(symbol, rng):
    paths = {
        "0": [arc(45, 48, 29, 39, 0, 2 * np.pi)],
        "1": [[[25, 26], [44, 10], [44, 87]], [[25, 87], [63, 87]]],
        "2": [[[14, 26], [19, 13], [39, 9], [61, 16], [70, 31], [60, 49], [16, 85], [72, 85]]],
        "3": [arc(37, 28, 28, 20, -2.0, 1.35) + arc(38, 66, 30, 23, -1.45, 2.0)],
        "4": [[[57, 10], [18, 57], [77, 57]], [[59, 12], [59, 89]]],
        "5": [
            [
                [71, 12],
                [23, 12],
                [20, 48],
                [41, 42],
                [61, 48],
                [71, 63],
                [62, 81],
                [41, 89],
                [18, 81],
            ]
        ],
        "6": [[[65, 10], [41, 20], [25, 40], [17, 65]] + arc(43, 65, 27, 24, np.pi, 3 * np.pi)],
        "7": [[[12, 14], [75, 14], [53, 47], [33, 90]]],
        "8": [
            arc(43, 29, 25, 21, np.pi / 2, 2.5 * np.pi)
            + arc(43, 69, 29, 24, -np.pi / 2, 1.5 * np.pi)
        ],
        "9": [arc(44, 33, 27, 23, 0, 2 * np.pi) + [[67, 58], [54, 83], [34, 91]]],
        "+": [[[10, 49], [45, 48], [81, 51]], [[46, 14], [45, 49], [48, 85]]],
        "-": [[[10, 49], [45, 48], [81, 51]]],
        "*": [[[14, 15], [78, 85]], [[79, 15], [13, 85]]],
        "(": [arc(67, 49, 42, 43, 2.0, 4.3)],
        ")": [arc(22, 49, 42, 43, -1.15, 1.15)],
        ".": [[[45, 85]]],
    }
    if symbol in {"/", "÷"}:
        paths[symbol] = (
            [[[45, 12], [46, 15]], [[10, 48], [80, 50]], [[46, 83], [46, 85]]]
            if symbol == "÷" or rng.random() < 0.5
            else [[[20, 86], [44, 49], [69, 11]]]
        )
    angle = rng.uniform(-0.13, 0.13)
    shear = rng.uniform(-0.09, 0.09)
    matrix = np.array([[np.cos(angle), -np.sin(angle) + shear], [np.sin(angle), np.cos(angle)]])
    matrix = matrix @ np.diag(rng.uniform([0.85, 0.92], [1.15, 1.08]))
    result = []
    for path in paths[symbol]:
        points = np.asarray(path, dtype=float)
        points += rng.normal(0, 0.55, points.shape)
        result.append(((points - [45, 50]) @ matrix.T + [50, 55]).tolist())
    return result


def render(strokes, width=6):
    """Share the application's antialiased rasterizer with synthetic pen data."""
    return rasterize(strokes, width)


def expression_cases(seed, count=240):
    rng = np.random.default_rng(seed)
    profiles = ["spaced", "tight", "decimal", "division", "broken", "slanted"]
    for index in range(count):
        profile = profiles[index % len(profiles)]
        a, b, c = rng.integers(1, 10, 3).astype(str)
        labels = list(f"{a}{rng.choice(['+', '-', '*', '/'])}{b}{c}")
        if profile == "decimal":
            labels = list(f"{a}.{b}+{c}")
        if profile == "division":
            labels = [a, "÷", b]
        strokes, boxes = [], []
        cursor = 30.0
        for label in labels:
            glyph = symbol_strokes(label, rng)
            points = np.asarray([point for stroke in glyph for point in stroke])
            lo, hi = points.min(axis=0), points.max(axis=0)
            gap = rng.uniform(3.5, 7) if profile in {"tight", "decimal"} else rng.uniform(18, 28)
            dx = cursor - lo[0]
            translated = [[[x + dx, y + 40] for x, y in stroke] for stroke in glyph]
            if profile == "broken" and label.isdigit():
                # Remove a small central section of a long pen segment.
                broken = []
                for stroke in translated:
                    lengths = [
                        np.linalg.norm(np.subtract(v, u))
                        for u, v in zip(stroke, stroke[1:], strict=False)
                    ]
                    if lengths and max(lengths) > 35:
                        at = int(np.argmax(lengths))
                        u, v = np.array(stroke[at]), np.array(stroke[at + 1])
                        mid = (u + v) / 2
                        direction = (v - u) / np.linalg.norm(v - u)
                        broken += [
                            stroke[: at + 1] + [(mid - direction * 3).tolist()],
                            [(mid + direction * 3).tolist()] + stroke[at + 1 :],
                        ]
                    else:
                        broken.append(stroke)
                translated = broken
            all_points = np.asarray([point for stroke in translated for point in stroke])
            low, high = all_points.min(axis=0), all_points.max(axis=0)
            boxes.append([*low, *high])
            strokes.extend(translated)
            cursor += hi[0] - lo[0] + gap
        if profile == "slanted":
            # Shear the whole expression without changing its reading order.
            strokes = [[[x + 0.12 * y, y] for x, y in stroke] for stroke in strokes]
            boxes = [
                [left + 0.12 * top, top, right + 0.12 * bottom, bottom]
                for left, top, right, bottom in boxes
            ]
        rng.shuffle(strokes)  # temporal pen order must not dictate spatial order
        yield {
            "profile": profile,
            "strokes": strokes,
            "boxes": boxes,
            "expression": "".join("/" if x == "÷" else x for x in labels),
        }
