import type { Stroke } from "./types";

export type InkHistory = {
  strokes: Stroke[];
  past: Stroke[][];
  future: Stroke[][];
};
export type InkAction =
  { type: "commit"; strokes: Stroke[] } | { type: "undo" } | { type: "redo" };
export const emptyInk: InkHistory = { strokes: [], past: [], future: [] };

export function inkHistory(state: InkHistory, action: InkAction): InkHistory {
  if (action.type === "commit") {
    if (action.strokes === state.strokes) return state;
    return {
      strokes: action.strokes,
      past: [...state.past, state.strokes].slice(-80),
      future: [],
    };
  }
  if (action.type === "undo") {
    if (!state.past.length) return state;
    return {
      strokes: state.past.at(-1)!,
      past: state.past.slice(0, -1),
      future: [state.strokes, ...state.future],
    };
  }
  if (!state.future.length) return state;
  return {
    strokes: state.future[0],
    past: [...state.past, state.strokes].slice(-80),
    future: state.future.slice(1),
  };
}
