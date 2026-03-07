import { describe, expect, it } from "vitest";
import { emptyInk, inkHistory } from "./inkHistory";
import type { Stroke } from "./types";

const first: Stroke = [
  [10, 10],
  [30, 40],
];
const second: Stroke = [
  [50, 50],
  [70, 80],
];
const third: Stroke = [
  [90, 90],
  [100, 120],
];

describe("drawing undo and redo", () => {
  it("restores the exact drawing after undo and redo", () => {
    let state = inkHistory(emptyInk, { type: "commit", strokes: [first] });
    state = inkHistory(state, { type: "commit", strokes: [first, second] });
    state = inkHistory(state, { type: "undo" });
    expect(state.strokes).toEqual([first]);
    state = inkHistory(state, { type: "redo" });
    expect(state.strokes).toEqual([first, second]);
  });
  it("discards the redo branch when a new stroke is drawn", () => {
    let state = inkHistory(emptyInk, { type: "commit", strokes: [first] });
    state = inkHistory(state, { type: "commit", strokes: [first, second] });
    state = inkHistory(state, { type: "undo" });
    state = inkHistory(state, { type: "commit", strokes: [first, third] });
    expect(state.future).toHaveLength(0);
    expect(inkHistory(state, { type: "redo" }).strokes).toEqual([first, third]);
  });
  it("allows a cleared drawing to be recovered", () => {
    let state = inkHistory(emptyInk, {
      type: "commit",
      strokes: [first, second],
    });
    state = inkHistory(state, { type: "commit", strokes: [] });
    expect(state.strokes).toEqual([]);
    expect(inkHistory(state, { type: "undo" }).strokes).toEqual([
      first,
      second,
    ]);
  });
  it("handles exhausted undo and redo without changing the drawing", () => {
    expect(inkHistory(emptyInk, { type: "undo" })).toBe(emptyInk);
    expect(inkHistory(emptyInk, { type: "redo" })).toBe(emptyInk);
  });
  it("bounds retained snapshots to avoid unbounded history", () => {
    let state = emptyInk;
    for (let i = 0; i < 100; i++) {
      state = inkHistory(state, { type: "commit", strokes: [[[i, i]]] });
    }
    expect(state.past).toHaveLength(80);
    expect(state.strokes).toEqual([[[99, 99]]]);
  });
});
