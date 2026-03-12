export type Point = [number, number];
export type Stroke = Point[];
export type Alternative = { label: string; confidence: number };
export type Token = Alternative & {
  predicted_label: string;
  method: "classifier" | "geometry";
  probabilities: Alternative[];
  input: { crop: string; normalized: string; width: number; height: number };
  corrected?: boolean;
  alternatives: Alternative[];
  thumbnail: string;
  box: number[];
};
export type Explanation = {
  supported: boolean;
  reason?: string;
  label?: string;
  baseline_confidence?: number;
  patch_size?: number;
  windows?: number;
  sensitivity?: number[][];
  max_abs_change?: number;
  min_change?: number;
  max_change?: number;
};
export type Calculation = {
  expression: string;
  result: string;
  steps: string[];
};
export type HistoryEntry = Calculation & { id: string; createdAt: string };
