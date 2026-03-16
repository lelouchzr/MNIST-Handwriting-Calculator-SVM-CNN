import { useId } from "react";
import type { Explanation } from "../types";

export function SensitivityMap({
  explanation,
  image,
  scale,
  modelName,
  showLegend = true,
}: {
  explanation: Explanation;
  image: string;
  scale?: number;
  modelName?: string;
  showLegend?: boolean;
}) {
  const id = useId().replaceAll(":", "");
  const rows = explanation.sensitivity ?? [];
  const magnitude = scale ?? explanation.max_abs_change ?? 0;
  return (
    <figure className="sensitivity-figure">
      <svg
        viewBox="0 0 28 28"
        className="sensitivity-map"
        role="img"
        aria-labelledby={`${id}-title ${id}-description`}
      >
        <title id={`${id}-title`}>
          Sensitivity of the {modelName ? `${modelName} ` : ""}prediction{" "}
          {explanation.label}
        </title>
        <desc id={`${id}-description`}>
          Yellow shows regions where masking lowered the original prediction
          score. Hatching shows where masking raised it. Overlapping 5 by 5
          windows are averaged.
        </desc>
        <defs>
          <pattern
            id={`${id}-hatch`}
            patternUnits="userSpaceOnUse"
            width="1"
            height="1"
          >
            <path d="M0 1L1 0" stroke="#20211f" strokeWidth="0.25" />
          </pattern>
        </defs>
        <image
          href={image}
          width="28"
          height="28"
          style={{ filter: "invert(1)", imageRendering: "pixelated" }}
        />
        {rows.flatMap((row, y) =>
          row.map((value, x) => (
            <g key={`${x}-${y}`}>
              <rect
                x={x}
                y={y}
                width="1"
                height="1"
                fill={value >= 0 ? "#f4ca48" : "#20211f"}
                opacity={
                  (Math.abs(value) / (magnitude || 1)) *
                  (value >= 0 ? 0.85 : 0.25)
                }
              >
                <title>
                  Average score change: {(value * 100).toFixed(2)} percentage
                  points
                </title>
              </rect>
              {value < 0 && (
                <rect
                  x={x}
                  y={y}
                  width="1"
                  height="1"
                  fill={`url(#${id}-hatch)`}
                  opacity={(Math.abs(value) / (magnitude || 1)) * 0.8}
                />
              )}
            </g>
          )),
        )}
      </svg>
      <figcaption>
        <span>−{(magnitude * 100).toFixed(1)} pp</span>
        <span>0</span>
        <span>+{(magnitude * 100).toFixed(1)} pp</span>
      </figcaption>
      {showLegend && <SensitivityLegend />}
    </figure>
  );
}

export function SensitivityLegend() {
  return (
    <div
      className="sensitivity-legend"
      aria-label="Effect of masking on the target score"
    >
      <span>
        <i className="legend-drop" aria-hidden="true" /> Score drops
      </span>
      <span>
        <i className="legend-rise" aria-hidden="true" /> Score rises
      </span>
    </div>
  );
}
