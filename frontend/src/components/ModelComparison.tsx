import { useEffect, useRef, useState } from "react";
import { ArrowClockwise } from "@phosphor-icons/react";
import { request } from "../api";
import type {
  ComparisonExplanation,
  Health,
  ModelId,
  Stroke,
  Token,
} from "../types";
import { SensitivityMap, SensitivityLegend } from "./SensitivityMap";
import {
  GeometryRule,
  InputPipeline,
  MaskingDiagram,
  SensitivityDetails,
} from "./RecognitionDiagrams";

import { InspectionTabs } from "./InspectionTabs";
import type { InspectionTab } from "./InspectionTabs";

const modelIds: ModelId[] = ["svm", "cnn"];
const score = (value: number) =>
  value > 0 && value < 0.001 ? "<0.1%" : `${(value * 100).toFixed(1)}%`;
type Props = {
  tokens: Token[];
  index: number | null;
  onSelect: (index: number, opener?: HTMLElement) => void;
  source: ModelId;
  onUseModel: (model: ModelId) => void;
  health: Health | null;
};

export function ModelComparison({
  tokens,
  index,
  onSelect,
  source,
  onUseModel,
  health,
}: Props) {
  const compared = tokens.filter((item) => item.agreement !== null);
  const different = compared.filter((item) => !item.agreement).length;
  return (
    <section className="comparison-panel" aria-labelledby="comparison-title">
      <div className="comparison-heading">
        <div>
          <h2 id="comparison-title">Compare predictions</h2>
        </div>
        <p>
          {compared.length
            ? `${different} ${different === 1 ? "disagreement" : "disagreements"} / ${compared.length} ${compared.length === 1 ? "symbol" : "symbols"}`
            : "Decimal marks use the shared size rule"}
        </p>
      </div>
      <p className="comparison-note">
        SVM: calibrated probability · CNN: uncalibrated softmax.
      </p>
      <div className="comparison-expressions">
        {modelIds.map((model) => (
          <div key={model}>
            <span className="model-name">{model.toUpperCase()}</span>
            <p>
              {tokens
                .map((item) => item.models[model]!.predicted_label)
                .join("")}
            </p>
            <button
              className={source === model ? "is-source" : ""}
              aria-pressed={source === model}
              onClick={() => onUseModel(model)}
            >
              {source === model
                ? `Using ${model.toUpperCase()} expression`
                : `Use ${model.toUpperCase()} expression`}
            </button>
          </div>
        ))}
      </div>
      <div className="comparison-metrics">
        {modelIds.map((model) => {
          const accuracy = health?.models[model]?.metrics.mnist_test_accuracy;
          return (
            <span key={model}>
              {model.toUpperCase()} held-out MNIST accuracy:{" "}
              {accuracy === undefined
                ? "unavailable"
                : `${(accuracy * 100).toFixed(2)}%`}
            </span>
          );
        })}
        <span>MNIST test · 2,000 digits.</span>
      </div>
      <table className="comparison-symbols">
        <caption className="sr-only">Per-symbol model predictions</caption>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>SVM</th>
            <th>CNN</th>
            <th>Agreement</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((item, position) => (
            <tr
              key={position}
              className={`${item.agreement === false ? "is-different" : ""} ${index === position ? "is-selected" : ""}`}
            >
              <th scope="row">
                <button
                  aria-label={`Compare symbol ${position + 1}`}
                  aria-pressed={index === position}
                  onClick={(event) => onSelect(position, event.currentTarget)}
                >
                  {position + 1}
                  <span>Inspect</span>
                </button>
              </th>
              {modelIds.map((model) => (
                <td key={model}>
                  <strong>{item.models[model]!.predicted_label}</strong>
                  <span>
                    {item.method === "geometry"
                      ? "size rule"
                      : score(item.models[model]!.confidence)}
                  </span>
                </td>
              ))}
              <td>
                {item.agreement === null
                  ? "Size rule"
                  : item.agreement
                    ? "Same"
                    : "Different"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function ComparisonInspector({
  tokens,
  index,
  strokes,
}: {
  tokens: Token[];
  index: number;
  strokes: Stroke[];
}) {
  const [tab, setTab] = useState<InspectionTab>("Predictions");
  const [result, setResult] = useState<{
    key: string;
    data: ComparisonExplanation;
  } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const cache = useRef(new Map<string, ComparisonExplanation>());
  const token = tokens[index];
  const svm = token.models.svm!;
  const cnn = token.models.cnn!;
  const key = `${index}:${svm.predicted_label}:${svm.confidence}:${cnn.predicted_label}:${cnn.confidence}:${token.input.normalized}`;
  const explanation = result?.key === key ? result.data : null;
  const error = failure?.key === key ? failure.message : null;

  useEffect(() => {
    if (tab !== "Explanation" || token.method === "geometry") return;
    const previous = cache.current.get(key);
    if (previous) {
      setResult({ key, data: previous });
      return;
    }
    const controller = new AbortController();
    setFailure(null);
    request<ComparisonExplanation>(
      "explain",
      { strokes, symbol_index: index, model: "compare" },
      AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
    )
      .then((data) => {
        if (controller.signal.aborted) return;
        for (const model of modelIds) {
          if (
            data.models[model].supported &&
            data.models[model].label !== token.models[model]?.predicted_label
          )
            throw new Error(
              "The model prediction changed. Recognize the drawing again.",
            );
        }
        cache.current.set(key, data);
        setResult({ key, data });
      })
      .catch((cause) => {
        if (controller.signal.aborted) return;
        setFailure({
          key,
          message:
            cause instanceof TypeError
              ? "The explanation service is unreachable. Please try again."
              : cause instanceof Error && cause.name === "TimeoutError"
                ? "The comparison took too long. Please try again."
                : cause instanceof Error
                  ? cause.message
                  : "The comparison could not be calculated.",
        });
      });
    return () => controller.abort();
  }, [index, key, tab, strokes, token.method, attempt]);

  return (
    <div className="comparison-details">
      {token.corrected && (
        <p className="inspector-edited">
          Edited → {token.label} · original model outputs
        </p>
      )}
      <div className="comparison-picks">
        {modelIds.map((model) => (
          <div key={model}>
            <span>{model.toUpperCase()} prediction</span>
            <strong>{token.models[model]!.predicted_label}</strong>
            <span>
              {token.method === "geometry"
                ? "size rule"
                : score(token.models[model]!.confidence)}
            </span>
          </div>
        ))}
      </div>
      <InspectionTabs value={tab} onChange={setTab} comparison>
        {tab === "Input" && <InputPipeline token={token} />}
        {tab === "Predictions" &&
          (token.method === "geometry" ? (
            <GeometryRule token={token} />
          ) : (
            <>
              <div className="diagram-meta">
                <span>16 classes · sorted by SVM</span>
                <span>CNN: uncalibrated</span>
              </div>
              <table className="comparison-scores">
                <caption className="sr-only">
                  Class scores for SVM and CNN
                </caption>
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>SVM probability</th>
                    <th>CNN softmax</th>
                  </tr>
                </thead>
                <tbody>
                  {svm.probabilities.map((item) => (
                    <tr key={item.label}>
                      <th scope="row">{item.label}</th>
                      {modelIds.map((model) => {
                        const value =
                          token.models[model]!.probabilities.find(
                            (candidate) => candidate.label === item.label,
                          )?.confidence ?? 0;
                        return (
                          <td key={model}>
                            <span
                              className="comparison-score-track"
                              aria-hidden="true"
                            >
                              <span style={{ width: `${value * 100}%` }} />
                            </span>
                            <span>{score(value)}</span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ))}
        {tab === "Explanation" &&
          (token.method === "geometry" ? (
            <GeometryRule token={token} />
          ) : error ? (
            <div className="inspector-failure" role="alert">
              <p>{error}</p>
              <button
                className="text-button"
                onClick={() => setAttempt((value) => value + 1)}
              >
                <ArrowClockwise size={16} />
                Try again
              </button>
            </div>
          ) : !explanation ? (
            <div className="explanation-loading" role="status">
              <p>Masking 576 regions for each model…</p>
            </div>
          ) : (
            <>
              <MaskingDiagram
                image={token.input.normalized}
                patchSize={explanation.models.svm.patch_size}
              />
              <div className="diagram-meta">
                <span>576 masks · averaged</span>
                <span>Shared scale · pp</span>
              </div>
              <SensitivityLegend />
              <div className="comparison-maps">
                {modelIds.map((model) => (
                  <section
                    key={model}
                    aria-label={`${model.toUpperCase()} explanation`}
                  >
                    <div className="map-heading">
                      <h4>
                        {model.toUpperCase()} ·{" "}
                        {explanation.models[model].label}
                      </h4>
                      <span>
                        {score(
                          explanation.models[model].baseline_confidence ?? 0,
                        )}
                      </span>
                    </div>
                    {explanation.models[model].supported ? (
                      <SensitivityMap
                        explanation={explanation.models[model]}
                        image={token.input.normalized}
                        scale={explanation.shared_max_abs_change}
                        modelName={model.toUpperCase()}
                        showLegend={false}
                      />
                    ) : (
                      <p>{explanation.models[model].reason}</p>
                    )}
                  </section>
                ))}
              </div>
              <SensitivityDetails />
            </>
          ))}
      </InspectionTabs>
    </div>
  );
}
