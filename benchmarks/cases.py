"""Independent geometric junction probes, separate from the pen-digit templates."""

import numpy as np


def junction_cases(seed=424242, per_profile=100):
    """Known component partitions, including near misses that must stay separate."""
    rng = np.random.default_rng(seed)
    profiles = (
        "junction_bottom",
        "junction_top",
        "no_contact",
        "adjacent_minuses",
        "parallel_neighbor",
        "decimal_neighbor",
        "interior_contact",
        "non_collinear",
    )
    for profile in profiles:
        for _ in range(per_profile):
            # Near-miss controls need clear ink separation even after pixel rounding.
            half_gap = (
                rng.uniform(4, 4.75)
                if profile in {"interior_contact", "non_collinear"}
                else rng.uniform(2, 3.75)
            )
            left = [[38, 100], [60 - half_gap, 100]]
            right = [[60 + half_gap, 100], [82, 100]]
            stem = [[[40, 35], [60, 20], [60, 62]], [[60, 68], [60, 100]]]
            groups = [stem + [left, right]]
            if profile == "junction_top":
                groups = [[[[60, 100], [46, 180]], left, right]]
            elif profile == "no_contact":
                stem[-1][-1][1] = 92
                groups = [stem, [left], [right]]
            elif profile == "adjacent_minuses":
                groups = [[left], [right]]
            elif profile == "parallel_neighbor":
                groups = [[[[110, 20], [110, 100]]], [left], [right]]
            elif profile == "decimal_neighbor":
                groups = [groups[0], [[[106, 100]]]]
            elif profile == "interior_contact":
                groups = [[[[60, 20], [60, 180]]], [left], [right]]
            elif profile == "non_collinear":
                right = [[60 + half_gap, 106], [82, 106]]
                groups = [stem, [left], [right]]
            angle = rng.uniform(-0.025, 0.025)
            scale = rng.uniform(0.85, 1.15)
            matrix = scale * np.array(
                [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
            )
            shift = rng.uniform(0, 100, 2)
            groups = [
                [(np.asarray(stroke) @ matrix.T + shift).tolist() for stroke in group]
                for group in groups
            ]
            boxes = []
            for group in groups:
                points = np.concatenate(group)
                boxes.append([*points.min(axis=0), *points.max(axis=0)])
            boxes.sort(key=lambda box: (box[0], box[1]))
            strokes = [stroke for group in groups for stroke in group]
            rng.shuffle(strokes)
            yield {"profile": profile, "strokes": strokes, "boxes": boxes}


def pixel_gap_cases(seed=67789, per_profile=100):
    """Independent continuous-coordinate partitions around pixel-rounding boundaries."""
    rng = np.random.default_rng(seed)
    profiles = (
        "vertical_neighbors",
        "bent_neighbors",
        "minus_neighbors",
        "crossing_plus",
        "shared_endpoint",
        "decimal_neighbor",
        "division_marks",
        "parentheses",
    )
    for profile in profiles:
        for _ in range(per_profile):
            gap = rng.uniform(3.05, 5)
            height = rng.uniform(60, 100)
            groups = [[[[40, 20], [40, 20 + height]]], [[[40 + gap, 20], [40 + gap, 20 + height]]]]
            if profile == "bent_neighbors":
                groups = [
                    [[[30, 20], [50, 60], [30, 100]]],
                    [[[50 + gap, 20], [70 + gap, 60], [50 + gap, 100]]],
                ]
            elif profile == "minus_neighbors":
                groups = [[[[30, 60], [60, 60]]], [[[60 + gap, 60], [90 + gap, 60]]]]
            elif profile == "crossing_plus":
                groups = [[[[60, 20], [60, 100]], [[30, 60], [90, 60]]]]
            elif profile == "shared_endpoint":
                groups = [[[[40, 20], [60, 60]], [[60, 60], [45, 100]]]]
            elif profile == "decimal_neighbor":
                groups = [[[[40, 20], [40, 100]]], [[[55, 100]]]]
            elif profile == "division_marks":
                groups = [[[[30, 60], [90, 60]], [[60, 30]], [[60, 90]]]]
            elif profile == "parentheses":
                angles = np.linspace(-1.1, 1.1, 30)
                groups = [
                    [
                        np.column_stack(
                            (60 - 20 * np.cos(angles), 60 + 40 * np.sin(angles))
                        ).tolist()
                    ],
                    [
                        np.column_stack(
                            (90 + 20 * np.cos(angles), 60 + 40 * np.sin(angles))
                        ).tolist()
                    ],
                ]
            shift = rng.uniform(0, 100, 2)  # fractional origins vary raster rounding
            groups = [[(np.asarray(path) + shift).tolist() for path in group] for group in groups]
            boxes = []
            for group in groups:
                points = np.concatenate(group)
                boxes.append([*points.min(axis=0), *points.max(axis=0)])
            boxes.sort(key=lambda box: (box[0], box[1]))
            strokes = [
                path[::-1] if rng.random() < 0.5 else path for group in groups for path in group
            ]
            rng.shuffle(strokes)
            yield {"profile": profile, "strokes": strokes, "boxes": boxes}
