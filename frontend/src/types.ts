export type Point = [number, number];
export type Stroke = Point[];
export type Alternative = { label: string; confidence: number };
export type ModelId = "svm" | "cnn";
export type RecognitionMode = ModelId | "compare";
export type ModelPrediction = {
  predicted_label: string;
  model_id: ModelId;
  score_kind: "calibrated_probability" | "uncalibrated_softmax" | "rule";
  method: "classifier" | "geometry";
  confidence: number;
  probabilities: Alternative[];
  alternatives: Alternative[];
};
export type Token = Alternative &
  ModelPrediction & {
    input: { crop: string; normalized: string; width: number; height: number };
    corrected?: boolean;
    thumbnail: string;
    box: number[];
    models: Partial<Record<ModelId, ModelPrediction>>;
    agreement: boolean | null;
  };
export type ModelStatus = {
  ready: boolean;
  name: string;
  score_kind: string;
  metrics: {
    mnist_test_accuracy?: number;
    synthetic_operator_test_accuracy?: number;
  };
  error?: string | null;
};
export type Health = {
  recognition_ready: boolean;
  model_error: string | null;
  models: Partial<Record<ModelId, ModelStatus>>;
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
  model_id?: ModelId;
};
export type ComparisonExplanation = {
  models: Record<ModelId, Explanation>;
  shared_max_abs_change: number;
};
export type Calculation = {
  expression: string;
  result: string;
  steps: string[];
};
export type HistoryEntry = Calculation & { id: string; createdAt: string };
