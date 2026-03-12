import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { X, ArrowClockwise } from "@phosphor-icons/react";
import { request } from "../api";
import type { Explanation, Stroke, Token } from "../types";
import { SensitivityMap } from "./SensitivityMap";

const tabs = ["Input", "Predictions", "Explanation"] as const;
type Tab = (typeof tabs)[number];
type Props = {
  tokens: Token[];
  index: number;
  strokes: Stroke[];
  onSelect: (index: number) => void;
  onClose: () => void;
};

function probability(value: number) {
  return value > 0 && value < 0.001 ? "<0.1%" : `${(value * 100).toFixed(1)}%`;
}

export function RecognitionInspector({
  tokens,
  index,
  strokes,
  onSelect,
  onClose,
}: Props) {
  const token = tokens[index];
  const [tab, setTab] = useState<Tab>("Input");
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
  const tabButtons = useRef<(HTMLButtonElement | null)[]>([]);
  const key = `${index}:${token.predicted_label}:${token.confidence}:${token.input.normalized}`;
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
      { strokes, symbol_index: index },
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

  function navigateTabs(
    event: KeyboardEvent<HTMLButtonElement>,
    position: number,
  ) {
    let next = position;
    if (event.key === "ArrowRight") next = (position + 1) % tabs.length;
    else if (event.key === "ArrowLeft")
      next = (position + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    setTab(tabs[next]);
    tabButtons.current[next]?.focus();
  }

  return (
    <section
      id="recognition-inspector"
      className="inspector-panel"
      tabIndex={-1}
      aria-labelledby="inspector-title"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          onClose();
        }
      }}
    >
      <div className="inspector-heading">
        <div>
          <p className="eyebrow">Recognition details</p>
          <h2 id="inspector-title">Inspect</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close inspector"
          onClick={onClose}
        >
          <X size={23} />
        </button>
      </div>
      <div className="inspector-selection">
        <label htmlFor="inspected-symbol">Symbol</label>
        <select
          id="inspected-symbol"
          value={index}
          onChange={(event) => onSelect(Number(event.target.value))}
        >
          {tokens.map((item, position) => (
            <option key={position} value={position}>
              {position + 1} / {tokens.length} · {item.label}
            </option>
          ))}
        </select>
      </div>
      <div className="inspector-prediction">
        <span>
          {token.method === "classifier" ? "Model prediction" : "Size rule"}
        </span>
        <strong>{token.predicted_label}</strong>
        {token.method === "classifier" && (
          <span>{probability(token.confidence)}</span>
        )}
      </div>
      {token.corrected && (
        <p className="inspector-edited">
          Expression edited to <strong>{token.label}</strong>. Inspection still
          describes the original recognition.
        </p>
      )}
      <div
        className="inspector-tabs"
        role="tablist"
        aria-label="Recognition inspection"
      >
        {tabs.map((name, position) => (
          <button
            key={name}
            ref={(element) => {
              tabButtons.current[position] = element;
            }}
            id={`inspect-tab-${name}`}
            role="tab"
            aria-selected={tab === name}
            aria-controls={`inspect-panel-${name}`}
            tabIndex={tab === name ? 0 : -1}
            onClick={() => setTab(name)}
            onKeyDown={(event) => navigateTabs(event, position)}
          >
            {name}
          </button>
        ))}
      </div>
      <div
        className="inspector-content"
        id={`inspect-panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`inspect-tab-${tab}`}
        tabIndex={0}
      >
        {tab === "Input" && (
          <>
            <h3>From strokes to pixels</h3>
            <figure className="input-crop">
              <div>
                <img
                  src={token.input.crop}
                  alt={`Rasterized crop of symbol ${index + 1}`}
                />
              </div>
              <figcaption>
                Original crop{" "}
                <span>
                  {token.input.width} × {token.input.height} px
                </span>
              </figcaption>
            </figure>
            <span className="input-transition" aria-hidden="true">
              ↓
            </span>
            <figure className="normalized-input">
              <div className="pixel-frame">
                <img
                  src={token.input.normalized}
                  width="224"
                  height="224"
                  alt={`Normalized 28 by 28 input for ${token.predicted_label}`}
                />
              </div>
              <figcaption>28 × 28 · normalized input</figcaption>
            </figure>
            <p className="inspector-note">
              Cropped to the ink, fitted within 20 × 20 pixels, then centered by
              mass on a 28 × 28 frame. Light pixels represent ink.
            </p>
            {token.method === "geometry" && (
              <p className="inspector-note">
                This normalized image is a preview only. The decimal-point rule
                uses the original drawing bounds.
              </p>
            )}
            <p className="inspector-footnote">
              Canvas bounds:{" "}
              {token.box.map((value) => Math.round(value)).join(", ")}.
            </p>
          </>
        )}
        {tab === "Predictions" &&
          (token.method === "geometry" ? (
            <div className="inspector-rule">
              <h3>Detected by size</h3>
              <p>
                This mark is smaller than 12 logical pixels. It is treated as a
                decimal point. No classifier probabilities were used.
              </p>
            </div>
          ) : (
            <>
              <h3>All {token.probabilities.length} classes</h3>
              <p className="inspector-note">
                Calibrated model estimates, sorted by score. A high score can
                still be wrong.
              </p>
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
              <p className="inspector-footnote">
                Lead over second place:{" "}
                {(
                  (token.probabilities[0].confidence -
                    token.probabilities[1].confidence) *
                  100
                ).toFixed(1)}{" "}
                percentage points.
              </p>
            </>
          ))}
        {tab === "Explanation" &&
          (token.method === "geometry" ? (
            <div className="inspector-rule">
              <h3>No model explanation</h3>
              <p>
                This decimal point was detected by size, not the classifier. A
                sensitivity map would not describe that rule.
              </p>
            </div>
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
              <small>Keeping the normalized input fixed.</small>
            </div>
          ) : !explanation.supported ? (
            <p className="inspector-note">{explanation.reason}</p>
          ) : (
            <>
              <h3>What changes the score?</h3>
              <p className="inspector-note">
                Each 5 × 5 region is masked to zero, then the model predicts
                again. Changes are averaged across overlapping windows.
              </p>
              <SensitivityMap
                explanation={explanation}
                image={token.input.normalized}
              />
              <p className="inspector-footnote">
                Original score for {explanation.label}:{" "}
                {probability(explanation.baseline_confidence ?? 0)} ·{" "}
                {explanation.windows} masks · pp = percentage points.
              </p>
              <p className="inspector-note">
                Colors are scaled per symbol. This measures sensitivity to
                masking, not a causal explanation.
              </p>
            </>
          ))}
      </div>
    </section>
  );
}
