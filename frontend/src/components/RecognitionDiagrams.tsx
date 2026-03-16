import { useId, useState } from "react";
import type { ReactNode } from "react";
import { ArrowDown, ArrowRight } from "@phosphor-icons/react";
import type { ModelId, ModelPrediction, Token } from "../types";

export function TechnicalDetails({ children }: { children: ReactNode }) {
  return (
    <details className="technical-details">
      <summary>Technical details</summary>
      {children}
    </details>
  );
}

export function GeometryRule({ token }: { token: Token }) {
  const side = Math.max(
    token.box[2] - token.box[0],
    token.box[3] - token.box[1],
  );
  return (
    <figure
      className="geometry-diagram"
      aria-label="Decimal point detected by size, without a classifier"
    >
      <div className="geometry-route">
        <img src={token.input.crop} alt="Detected mark" />
        <div>
          <span className="diagram-mono">{side.toFixed(1)} &lt; 12 px</span>
          <ArrowRight size={24} aria-hidden="true" />
        </div>
        <strong>.</strong>
      </div>
      <figcaption>Size rule · no classifier</figcaption>
    </figure>
  );
}

function FeatureGlyph({ model }: { model: ModelId }) {
  return (
    <svg viewBox="0 0 100 48" className="feature-glyph" aria-hidden="true">
      {model === "svm"
        ? Array.from({ length: 15 }, (_, index) => {
            const x = 10 + (index % 5) * 20;
            const y = 8 + Math.floor(index / 5) * 16;
            return (
              <g
                key={index}
                transform={`translate(${x} ${y}) rotate(${index * 37})`}
              >
                <path
                  d="M-6 0H6 M0-5V5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                />
              </g>
            );
          })
        : [0, 1, 2].map((layer) => (
            <g
              key={layer}
              transform={`translate(${28 + layer * 8} ${13 - layer * 5})`}
            >
              <rect
                width="30"
                height="30"
                fill={layer === 2 ? "#f5edcc" : "#fff"}
                stroke="currentColor"
              />
              <path d="M10 0V30 M20 0V30 M0 10H30 M0 20H30" stroke="#cecec7" />
              <rect x="10" y="10" width="10" height="10" fill="#f4ca48" />
            </g>
          ))}
    </svg>
  );
}

function ScoreDistribution({ prediction }: { prediction: ModelPrediction }) {
  const labels = [..."0123456789", "+", "−", "×", "÷", "(", ")"];
  return (
    <svg
      viewBox="0 0 144 34"
      className="mini-distribution"
      role="img"
      aria-label={`${prediction.model_id.toUpperCase()} distribution over 16 classes`}
    >
      {labels.map((label, index) => {
        const confidence =
          prediction.probabilities.find((item) => item.label === label)
            ?.confidence ?? 0;
        const height = Math.max(0, Math.min(1, confidence)) * 30;
        return (
          <rect
            key={label}
            x={index * 9}
            y={32 - height}
            width="6"
            height={height}
            fill={label === prediction.predicted_label ? "#f4ca48" : "#aaa99f"}
          >
            <title>
              {label}: {(confidence * 100).toFixed(1)}%
            </title>
          </rect>
        );
      })}
      <path d="M0 33H144" stroke="#cecec7" />
    </svg>
  );
}

export function InputPipeline({ token }: { token: Token }) {
  if (token.method === "geometry") return <GeometryRule token={token} />;
  const models = (["svm", "cnn"] as const).filter(
    (model) => token.models[model],
  );
  return (
    <div className="input-pipeline">
      <div className="pixel-route">
        <figure>
          <div className="pipeline-preview">
            <img src={token.input.crop} alt="Raster crop" />
          </div>
          <figcaption>
            Crop{" "}
            <small>
              {token.input.width} × {token.input.height}
            </small>
          </figcaption>
        </figure>
        <div className="pipeline-transform">
          <span>Fit ≤20</span>
          <ArrowRight size={22} aria-hidden="true" />
          <span>Center</span>
        </div>
        <figure>
          <div className="pipeline-preview normalized">
            <img
              src={token.input.normalized}
              alt="Normalized 28 by 28 model input"
            />
          </div>
          <figcaption>
            28 × 28 <small>Input</small>
          </figcaption>
        </figure>
      </div>
      <svg viewBox="0 0 300 28" className="pipeline-split" aria-hidden="true">
        {models.length === 2 ? (
          <path d="M150 0V10H75V26 M150 10H225V26 M71 22L75 26L79 22 M221 22L225 26L229 22" />
        ) : (
          <path d="M150 0V26 M146 22L150 26L154 22" />
        )}
      </svg>
      <div
        className={`model-routes ${models.length === 1 ? "single-route" : ""}`}
      >
        {models.map((model) => (
          <figure
            key={model}
            className="model-route"
            aria-label={`${model.toUpperCase()} recognition pipeline`}
          >
            <div className="feature-stage">
              <FeatureGlyph model={model} />
              <span>{model === "svm" ? "HOG" : "Conv ×2"}</span>
              <small>
                {model === "svm" ? "324 features" : "3 × 3 kernels"}
              </small>
            </div>
            <ArrowDown size={18} aria-hidden="true" />
            <strong>{model.toUpperCase()}</strong>
            <ArrowDown size={18} aria-hidden="true" />
            <ScoreDistribution prediction={token.models[model]!} />
            <figcaption>16 scores</figcaption>
          </figure>
        ))}
      </div>
      <TechnicalDetails>
        <p>
          Crop to the ink, fit within 20 × 20 pixels, then center by mass on a
          28 × 28 frame. The diagrams show model architecture; the score bars
          use the actual predictions.
        </p>
        <dl>
          <dt>Canvas bounds</dt>
          <dd>{token.box.map(Math.round).join(", ")}</dd>
        </dl>
      </TechnicalDetails>
    </div>
  );
}

export function MaskingDiagram({
  image,
  patchSize = 5,
}: {
  image: string;
  patchSize?: number;
}) {
  const sliderId = useId();
  const across = 28 - patchSize + 1;
  const total = across * across;
  const [position, setPosition] = useState(
    Math.floor((across - 1) / 2) * (across + 1),
  );
  const x = position % across;
  const y = Math.floor(position / across);
  return (
    <figure className="masking-diagram">
      <div
        className="masking-route"
        role="group"
        aria-label="Occlusion method: input, zero mask, then rescore the original class"
      >
        <div>
          <svg viewBox="0 0 28 28" role="img" aria-label="Fixed model input">
            <image
              href={image}
              width="28"
              height="28"
              style={{ filter: "invert(1)", imageRendering: "pixelated" }}
            />
          </svg>
          <span>Input</span>
        </div>
        <ArrowRight size={16} aria-hidden="true" />
        <div>
          <svg
            viewBox="0 0 28 28"
            role="img"
            aria-label={`Zero mask at column ${x + 1}, row ${y + 1}`}
          >
            <image
              href={image}
              width="28"
              height="28"
              style={{ filter: "invert(1)", imageRendering: "pixelated" }}
            />
            <rect
              data-testid="mask-window"
              x={x}
              y={y}
              width={patchSize}
              height={patchSize}
              fill="white"
              stroke="#f4ca48"
              strokeWidth="0.65"
            />
          </svg>
          <span>
            {patchSize} × {patchSize} zero
          </span>
        </div>
        <ArrowRight size={16} aria-hidden="true" />
        <div>
          <svg
            viewBox="0 0 60 60"
            role="img"
            aria-label="Rescore the original class, then subtract masked from original score"
          >
            <text
              x="30"
              y="40"
              textAnchor="middle"
              fontSize="32"
              fontFamily="monospace"
              fill="#20211f"
            >
              Δ
            </text>
          </svg>
          <span>Δ score</span>
        </div>
      </div>
      <div className="mask-preview-control">
        <label htmlFor={sliderId}>Mask preview</label>
        <output htmlFor={sliderId}>
          {position + 1} / {total}
        </output>
        <input
          id={sliderId}
          type="range"
          min="0"
          max={total - 1}
          step="1"
          value={position}
          aria-valuetext={`Position ${position + 1} of ${total}, column ${x + 1}, row ${y + 1}`}
          onChange={(event) => setPosition(Number(event.target.value))}
        />
      </div>
      <figcaption>
        Δ = original − masked <span>Maps average all masks</span>
      </figcaption>
    </figure>
  );
}

export function SensitivityDetails() {
  return (
    <TechnicalDetails>
      <p>
        Each zero mask is scored against the original top class on the fixed
        input. Each map pixel averages the signed effects of all covering
        windows. The slider previews the mask position; it does not recompute
        the averaged maps.
      </p>
      <p>
        pp = percentage points. Yellow means masking lowered the target score;
        hatching means it raised it. This measures perturbation sensitivity, not
        causality or model accuracy. Compare uses one color scale for both
        models, each explaining its own top class.
      </p>
    </TechnicalDetails>
  );
}
