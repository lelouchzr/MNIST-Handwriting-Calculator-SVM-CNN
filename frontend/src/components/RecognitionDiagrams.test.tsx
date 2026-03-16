// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { InputPipeline, MaskingDiagram } from "./RecognitionDiagrams";
import type { ModelPrediction, Token } from "../types";

const svm: ModelPrediction = {
  model_id: "svm",
  predicted_label: "2",
  confidence: 0.9,
  method: "classifier",
  score_kind: "calibrated_probability",
  probabilities: [
    { label: "2", confidence: 0.9 },
    { label: "7", confidence: 0.1 },
  ],
  alternatives: [{ label: "2", confidence: 0.9 }],
};
const token: Token = {
  ...svm,
  label: "2",
  thumbnail: "crop.png",
  box: [0, 0, 40, 80],
  input: { crop: "crop.png", normalized: "input.png", width: 56, height: 96 },
  models: { svm },
  agreement: null,
};
afterEach(cleanup);

describe("diagrams use the selected input and recorded outputs", () => {
  it("shows the actual images and SVM scores without inventing a CNN output", () => {
    render(<InputPipeline token={token} />);
    expect(screen.getByAltText("Raster crop").getAttribute("src")).toBe(
      "crop.png",
    );
    expect(
      screen
        .getByAltText("Normalized 28 by 28 model input")
        .getAttribute("src"),
    ).toBe("input.png");
    const chart = screen.getByRole("img", {
      name: "SVM distribution over 16 classes",
    });
    expect(within(chart).getByText("2: 90.0%")).toBeTruthy();
    expect(within(chart).getByText("7: 10.0%")).toBeTruthy();
    expect(
      screen.queryByRole("img", { name: "CNN distribution over 16 classes" }),
    ).toBeNull();
    expect(screen.getByText("Technical details").closest("details")?.open).toBe(
      false,
    );
  });
  it("keeps separate recorded distributions for both model branches", () => {
    const cnn = {
      ...svm,
      model_id: "cnn" as const,
      probabilities: [{ label: "2", confidence: 0.65 }],
    };
    render(<InputPipeline token={{ ...token, models: { svm, cnn } }} />);
    expect(
      within(
        screen.getByRole("img", { name: "SVM distribution over 16 classes" }),
      ).getByText("2: 90.0%"),
    ).toBeTruthy();
    expect(
      within(
        screen.getByRole("img", { name: "CNN distribution over 16 classes" }),
      ).getByText("2: 65.0%"),
    ).toBeTruthy();
  });
  it("bypasses the classifiers for a geometric decimal point", () => {
    render(
      <InputPipeline
        token={{
          ...token,
          method: "geometry",
          predicted_label: ".",
          label: ".",
          box: [10, 10, 13, 14],
        }}
      />,
    );
    expect(screen.getByText("4.0 < 12 px")).toBeTruthy();
    expect(screen.getByText("Size rule · no classifier")).toBeTruthy();
    expect(screen.queryByRole("img", { name: /distribution/ })).toBeNull();
  });
  it("moves the zero-mask preview across every valid position without crossing the input boundary", () => {
    render(<MaskingDiagram image="input.png" />);
    const slider = screen.getByRole("slider", { name: "Mask preview" });
    const mask = screen.getByTestId("mask-window");
    fireEvent.change(slider, { target: { value: "0" } });
    expect(mask.getAttribute("x")).toBe("0");
    expect(mask.getAttribute("y")).toBe("0");
    expect(slider.getAttribute("aria-valuetext")).toContain(
      "Position 1 of 576",
    );
    fireEvent.change(slider, { target: { value: "575" } });
    expect(mask.getAttribute("x")).toBe("23");
    expect(mask.getAttribute("y")).toBe("23");
    expect(mask.getAttribute("width")).toBe("5");
    expect(mask.getAttribute("height")).toBe("5");
    expect(slider.getAttribute("aria-valuetext")).toContain(
      "column 24, row 24",
    );
    expect(screen.getByText("Maps average all masks")).toBeTruthy();
  });
});
