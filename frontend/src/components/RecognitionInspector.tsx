import { useEffect, useRef, useState } from "react";
import { ArrowClockwise } from "@phosphor-icons/react";
import { request } from "../api";
import type { Explanation, Stroke, Token } from "../types";
import { SensitivityMap } from "./SensitivityMap";
import {
  GeometryRule,
  InputPipeline,
  MaskingDiagram,
  SensitivityDetails,
} from "./RecognitionDiagrams";
import { InspectionTabs } from "./InspectionTabs";
import type { InspectionTab } from "./InspectionTabs";

type Props = {
  tokens: Token[];
  index: number;
  strokes: Stroke[];
};

function probability(value: number) {
  return value > 0 && value < 0.001 ? "<0.1%" : `${(value * 100).toFixed(1)}%`;
}

export function RecognitionInspector({ tokens, index, strokes }: Props) {
  const token = tokens[index];
  const [tab, setTab] = useState<InspectionTab>("Input");
  const [result, setResult] = useState<{
    key: string;
    value: Explanation;
  } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const cache = useRef(new Map<string, Explanation>());
  const key = `${token.model_id}:${index}:${token.predicted_label}:${token.confidence}:${token.input.normalized}`;
  const explanation = result?.key === key ? result.value : null;
  const error = failure?.key === key ? failure.message : null;

  useEffect(() => {
    if (tab !== "Explanation" || token.method === "geometry") return;
    const previous = cache.current.get(key);
    if (previous) {
      setResult({ key, value: previous });
      return;
    }
    const controller = new AbortController();
    setFailure(null);
    request<Explanation>(
      "explain",
      { strokes, symbol_index: index, model: token.model_id },
      AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
    )
      .then((value) => {
        if (controller.signal.aborted) return;
        if (value.supported && value.label !== token.predicted_label)
          throw new Error(
            "The model prediction changed. Recognize the drawing again.",
          );
        cache.current.set(key, value);
        setResult({ key, value });
      })
      .catch((cause) => {
        if (controller.signal.aborted) return;
        const message =
          cause instanceof TypeError
            ? "The explanation service is unreachable. Please try again."
            : cause instanceof Error && cause.name === "TimeoutError"
              ? "The explanation took too long. Please try again."
              : cause instanceof Error
                ? cause.message
                : "The explanation could not be calculated.";
        setFailure({ key, message });
      });
    return () => controller.abort();
  }, [tab, key, index, strokes, token.method, token.predicted_label, attempt]);

  return (
    <div className="inspector-panel">
      <div className="inspector-prediction">
        <span>
          {token.method === "classifier"
            ? `${token.model_id.toUpperCase()} prediction`
            : "Size rule"}
        </span>
        <strong>{token.predicted_label}</strong>
        {token.method === "classifier" && (
          <span>{probability(token.confidence)}</span>
        )}
      </div>
      {token.corrected && (
        <p className="inspector-edited">
          Edited → <strong>{token.label}</strong> · original model output
        </p>
      )}
      <InspectionTabs value={tab} onChange={setTab}>
        {tab === "Input" && <InputPipeline token={token} />}
        {tab === "Predictions" &&
          (token.method === "geometry" ? (
            <GeometryRule token={token} />
          ) : (
            <>
              <div className="diagram-meta">
                <span>{token.probabilities.length} classes</span>
                <span>
                  {token.model_id === "cnn"
                    ? "Softmax · uncalibrated"
                    : "Calibrated probability"}
                </span>
              </div>
              <ol className="probability-list" aria-label="Class probabilities">
                {token.probabilities.map((item, position) => (
                  <li
                    key={item.label}
                    className={position === 0 ? "top-prediction" : ""}
                  >
                    <span className="probability-label">{item.label}</span>
                    <span className="probability-track" aria-hidden="true">
                      <span style={{ width: `${item.confidence * 100}%` }} />
                    </span>
                    <span className="probability-value">
                      {probability(item.confidence)}
                    </span>
                  </li>
                ))}
              </ol>
              <div className="score-gap">
                <span>Top-2 gap</span>
                <strong>
                  {" "}
                  {(
                    (token.probabilities[0].confidence -
                      token.probabilities[1].confidence) *
                    100
                  ).toFixed(1)}{" "}
                  pp
                </strong>
              </div>
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
                <ArrowClockwise size={17} />
                Try again
              </button>
            </div>
          ) : !explanation ? (
            <div className="explanation-loading" role="status">
              <span aria-hidden="true">⋯</span>
              <p>Masking 576 regions…</p>
            </div>
          ) : !explanation.supported ? (
            <p className="inspector-note">{explanation.reason}</p>
          ) : (
            <>
              <MaskingDiagram
                image={token.input.normalized}
                patchSize={explanation.patch_size}
              />
              <SensitivityMap
                explanation={explanation}
                image={token.input.normalized}
              />
              <div className="diagram-meta">
                <span>{explanation.windows} masks</span>
                <span>Per-symbol scale · pp</span>
              </div>
              <SensitivityDetails />
            </>
          ))}
      </InspectionTabs>
    </div>
  );
}
