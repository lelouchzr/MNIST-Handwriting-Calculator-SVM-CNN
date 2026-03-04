export type Point = [number, number];
export type Stroke = Point[];
export type Alternative = { label: string; confidence: number };
export type Token = Alternative & {
  alternatives: Alternative[];
  thumbnail: string;
  box: number[];
};
export type Calculation = {
  expression: string;
  result: string;
  steps: string[];
};
export type HistoryEntry = Calculation & { id: string; createdAt: string };
