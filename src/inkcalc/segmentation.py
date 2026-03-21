"""Spatial pen segmentation, independent of either classifier."""

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label


@dataclass
class Segment:
    image: Image.Image
    box: list[float]

    @property
    def is_point(self):
        width, height = self.box[2] - self.box[0], self.box[3] - self.box[1]
        side = max(width, height)
        # A short horizontal minus must not become a decimal point.
        return side < 12 and (side <= 3 or min(width, height) >= 0.35 * side)


def rasterize(strokes, width=6):
    points = np.asarray([point for stroke in strokes for point in stroke])
    left, top = points.min(axis=0)
    right, bottom = points.max(axis=0)
    size = (max(1, int(np.ceil(right - left))) + 16, max(1, int(np.ceil(bottom - top))) + 16)
    image = Image.new("L", (size[0] * 3, size[1] * 3))
    draw = ImageDraw.Draw(image)
    for stroke in strokes:
        xy = [(round((x - left + 8) * 3), round((y - top + 8) * 3)) for x, y in stroke]
        if len(xy) > 1:
            draw.line(xy, fill=255, width=round(width * 3), joint="curve")
        for x, y in (xy[0], xy[-1]):
            radius = width * 1.5
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    return image.resize(size, Image.Resampling.LANCZOS)


def bounds(strokes):
    points = np.asarray([point for stroke in strokes for point in stroke])
    return [*points.min(axis=0), *points.max(axis=0)]


def segment_strokes(strokes):
    if not strokes:
        return []
    boxes = [bounds([stroke]) for stroke in strokes]
    left = min(box[0] for box in boxes) - 4
    top = min(box[1] for box in boxes) - 4
    right = max(box[2] for box in boxes) + 4
    bottom = max(box[3] for box in boxes) + 4
    if right - left > 1010 or bottom - top > 1010:
        raise ValueError("Drawing bounds exceed 1000 logical pixels.")
    # Thin centerlines connect crossing/meeting strokes without conflating nearby glyphs.
    image = Image.new("L", (int(np.ceil(right - left)) + 1, int(np.ceil(bottom - top)) + 1))
    draw = ImageDraw.Draw(image)
    starts = []
    for stroke in strokes:
        xy = [(round(x - left), round(y - top)) for x, y in stroke]
        starts.append(xy[0])
        if len(xy) > 1:
            draw.line(xy, fill=1, width=3, joint="curve")
        else:
            x, y = xy[0]
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
    components, _ = label(np.asarray(image), structure=np.ones((3, 3)))
    grouped = {}
    for stroke, (x, y) in zip(strokes, starts, strict=True):
        grouped.setdefault(int(components[y, x]), []).append(stroke)
    groups = []
    for connected in grouped.values():
        # Pixel rounding and 8-connectivity can bridge a real horizontal gap.
        # Require continuous x support within the 3 px pen radius as well.
        current, reach = [], -np.inf
        for stroke in sorted(connected, key=lambda path: bounds([path])[0]):
            box = bounds([stroke])
            if current and box[0] - reach > 3:
                groups.append(current)
                current = []
            current.append(stroke)
            reach = max(reach, box[2])
        groups.append(current)
    parents = list(range(len(groups)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def merge(a, b):
        parents[root(b)] = root(a)

    group_boxes = [bounds(group) for group in groups]
    heights = [b[3] - b[1] for b in group_boxes if b[3] - b[1] > 12]
    height = max(float(np.percentile(heights, 75)) if heights else 60.0, (bottom - top - 8) * 0.8)

    def endpoints(group):
        result = []
        for stroke in group:
            for path in (stroke, stroke[::-1]):
                point = np.asarray(path[0])
                for other in path[1:]:
                    vector = point - other
                    length = np.linalg.norm(vector)
                    if length > 1e-6:
                        result.append((point, vector / length))
                        break
        return result

    # Repair small vertical breaks inside a glyph; overlapping vertical spans do not qualify.
    for i, a in enumerate(group_boxes):
        for j in range(i + 1, len(group_boxes)):
            b = group_boxes[j]
            overlap = min(a[2], b[2]) - max(a[0], b[0]) + 4
            gap = max(a[1], b[1]) - min(a[3], b[3])
            narrow = max(4, min(a[2] - a[0], b[2] - b[0]) + 4)
            small = min(a[3] - a[1], b[3] - b[1]) <= height * 0.45
            if small and overlap >= narrow * 0.6 and 0 < gap <= max(4, height * 0.12):
                # Isolated compact dots are reserved for decimals and division assembly.
                a_point = max(a[2] - a[0], a[3] - a[1]) < 12
                b_point = max(b[2] - b[0], b[3] - b[1]) < 12
                if not a_point and not b_point:
                    merge(i, j)
    joined = {}
    for index, group in enumerate(groups):
        joined.setdefault(root(index), []).extend(group)
    groups = list(joined.values())
    group_boxes = [bounds(group) for group in groups]
    parents = list(range(len(groups)))
    ends = [endpoints(group) for group in groups]
    gap_limit = min(10, max(4, height * 0.12))

    def junction_anchor(i, j, start, direction, length):
        """A third stroke can end in the missing section of a horizontal foot.

        Require contact within the pen radius, inside the gap, and a transverse
        endpoint on a tall component. Two neighboring minus signs lack this
        junction evidence and must remain separate.
        """
        anchors = set()
        for k, box in enumerate(group_boxes):
            if k in (i, j) or box[3] - box[1] < height * 0.5:
                continue
            for point, tangent in ends[k]:
                offset = point - start
                along = np.dot(offset, direction)
                across = np.linalg.norm(offset - along * direction)
                if 0 <= along <= length and across <= 3 and abs(np.dot(tangent, direction)) < 0.35:
                    anchors.add(k)
        # Ambiguous contact with two separate glyphs is insufficient evidence.
        return anchors.pop() if len(anchors) == 1 else None

    # Repair interrupted pen strokes only when both tangents continue across the gap.
    for i, a in enumerate(group_boxes):
        for j in range(i + 1, len(group_boxes)):
            b = group_boxes[j]
            if max(a[3] - a[1], b[3] - b[1]) < 4:
                continue
            if min(a[3] - a[1], b[3] - b[1]) > height * 0.75:
                continue
            if max(a[2], b[2]) - min(a[0], b[0]) > height * 1.15:
                continue
            if max(a[0], b[0]) - min(a[2], b[2]) > gap_limit:
                continue
            if max(a[1], b[1]) - min(a[3], b[3]) > gap_limit:
                continue
            for point_a, tangent_a in ends[i]:
                for point_b, tangent_b in ends[j]:
                    direction = point_b - point_a
                    length = np.linalg.norm(direction)
                    if 0 < length <= gap_limit:
                        direction = direction / length
                        if (
                            np.dot(tangent_a, direction) > 0.9
                            and np.dot(tangent_b, -direction) > 0.9
                        ):
                            merge(i, j)
    joined = {}
    for index, group in enumerate(groups):
        joined.setdefault(root(index), []).extend(group)
    groups = list(joined.values())
    group_boxes = [bounds(group) for group in groups]
    parents = list(range(len(groups)))
    ends = [endpoints(group) for group in groups]
    # Rebuild components first: an interrupted stem may only now be a tall anchor.
    # Keeping this as a separate pass makes contact evidence independent of pen order.
    for i, a in enumerate(group_boxes):
        for j in range(i + 1, len(group_boxes)):
            b = group_boxes[j]
            if max(a[3] - a[1], b[3] - b[1]) >= 4:
                continue
            if max(a[2], b[2]) - min(a[0], b[0]) > height * 1.15:
                continue
            if max(a[0], b[0]) - min(a[2], b[2]) > gap_limit:
                continue
            if max(a[1], b[1]) - min(a[3], b[3]) > gap_limit:
                continue
            for point_a, tangent_a in ends[i]:
                for point_b, tangent_b in ends[j]:
                    direction = point_b - point_a
                    length = np.linalg.norm(direction)
                    if 0 < length <= gap_limit:
                        direction = direction / length
                        if (
                            np.dot(tangent_a, direction) > 0.9
                            and np.dot(tangent_b, -direction) > 0.9
                        ):
                            anchor = junction_anchor(i, j, point_a, direction, length)
                            if anchor is not None:
                                merge(i, anchor)
                                merge(i, j)
    joined = {}
    for index, group in enumerate(groups):
        joined.setdefault(root(index), []).extend(group)
    groups = list(joined.values())
    group_boxes = [bounds(group) for group in groups]
    parents = list(range(len(groups)))
    # A division operator requires a bar AND aligned dots on both sides.
    for i, bar in enumerate(group_boxes):
        width, thickness = bar[2] - bar[0], bar[3] - bar[1]
        if width < height * 0.3 or thickness > max(5, width * 0.18):
            continue
        cx, cy = (bar[0] + bar[2]) / 2, (bar[1] + bar[3]) / 2
        above, below = [], []
        for j, dot in enumerate(group_boxes):
            if i == j:
                continue
            extent = max(dot[2] - dot[0], dot[3] - dot[1])
            dx, dy = (dot[0] + dot[2]) / 2 - cx, (dot[1] + dot[3]) / 2 - cy
            if extent <= max(12, width * 0.22) and abs(dx) <= width * 0.25:
                if max(5, height * 0.1) <= abs(dy) <= min(height * 0.85, width * 0.9):
                    (above if dy < 0 else below).append((abs(dx) + abs(dy), j))
        if above and below:
            merge(i, min(above)[1])
            merge(i, min(below)[1])
    merged = {}
    for i, group in enumerate(groups):
        merged.setdefault(root(i), []).extend(group)
    result = [Segment(rasterize(group), bounds(group)) for group in merged.values()]
    result.sort(key=lambda segment: (segment.box[0], segment.box[1]))
    if len(result) > 64:
        raise ValueError("Limit the expression to 64 symbols.")
    return result
