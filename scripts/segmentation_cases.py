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
