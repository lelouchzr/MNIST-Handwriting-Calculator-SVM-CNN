import type { Point, Stroke } from "./types";

// Original pen paths: useful both as a demo and a repeatable recognition smoke test.
const glyphs: Record<string, Stroke[]> = {
  "1": [
    [
      [8, 18],
      [22, 4],
      [22, 80],
    ],
    [
      [10, 80],
      [36, 80],
    ],
  ],
  "2": [
    [
      [2, 20],
      [7, 8],
      [19, 3],
      [32, 7],
      [39, 18],
      [36, 30],
      [27, 42],
      [4, 77],
      [41, 77],
    ],
  ],
  "7": [
    [
      [0, 7],
      [43, 7],
      [31, 29],
      [22, 51],
      [14, 80],
    ],
  ],
  "+": [
    [
      [0, 40],
      [45, 40],
    ],
    [
      [22, 17],
      [22, 64],
    ],
  ],
};

export function sampleExpression(): Stroke[] {
  return ["1", "2", "+", "7"].flatMap((glyph, index) =>
    glyphs[glyph].map((stroke) =>
      stroke.map(([x, y]): Point => [
        x * 1.65 + 215 + index * 145,
        y * 1.65 + 100,
      ]),
    ),
  );
}
