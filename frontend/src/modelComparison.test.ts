import { describe, expect, it } from "vitest";
import { tokensForModel } from "./modelComparison";
import type { ModelPrediction, Token } from "./types";

const svm: ModelPrediction = {
  model_id: "svm",
  predicted_label: "7",
  confidence: 0.8,
  method: "classifier",
  score_kind: "calibrated_probability",
  probabilities: [{ label: "7", confidence: 0.8 }],
  alternatives: [{ label: "7", confidence: 0.8 }],
};
const cnn: ModelPrediction = {
  ...svm,
  model_id: "cnn",
  predicted_label: "2",
  confidence: 0.51,
  score_kind: "uncalibrated_softmax",
  probabilities: [{ label: "2", confidence: 0.51 }],
};
const token: Token = {
  ...svm,
  label: "3",
  corrected: true,
  thumbnail: "preview",
  box: [0, 0, 20, 30],
  input: { crop: "crop", normalized: "normalized", width: 20, height: 30 },
  models: { svm, cnn },
  agreement: false,
};

describe("explicit expression source", () => {
  it("switches expression labels and scores without rewriting either model output", () => {
    const changed = tokensForModel([token], "cnn")![0];
    expect(changed.label).toBe("2");
    expect(changed.predicted_label).toBe("2");
    expect(changed.model_id).toBe("cnn");
    expect(changed.confidence).toBe(0.51);
    expect(changed.corrected).toBe(false);
    expect(changed.models).toBe(token.models);
    expect(changed.agreement).toBe(false);
    expect(token.label).toBe("3");
    expect(token.models.svm?.predicted_label).toBe("7");
  });
  it("can switch back to the original SVM prediction", () => {
    const cnnTokens = tokensForModel([token], "cnn")!;
    expect(tokensForModel(cnnTokens, "svm")![0].label).toBe("7");
  });
  it("does not partially replace an expression if a model is missing", () => {
    expect(
      tokensForModel([token, { ...token, models: { svm } }], "cnn"),
    ).toBeNull();
  });
  it("preserves the geometric decimal rule", () => {
    const point: ModelPrediction = {
      ...svm,
      predicted_label: ".",
      method: "geometry",
      score_kind: "rule",
      probabilities: [],
      alternatives: [{ label: ".", confidence: 1 }],
    };
    const changed = tokensForModel(
      [
        {
          ...token,
          agreement: null,
          models: { svm: point, cnn: { ...point, model_id: "cnn" } },
        },
      ],
      "cnn",
    )![0];
    expect(changed.label).toBe(".");
    expect(changed.method).toBe("geometry");
    expect(changed.probabilities).toEqual([]);
    expect(changed.agreement).toBeNull();
  });
});
