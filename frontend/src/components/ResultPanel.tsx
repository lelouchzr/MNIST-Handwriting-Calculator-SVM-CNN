import type { Calculation } from "../types";

export function displayExpression(expression: string) {
  return expression
    .replaceAll("*", " × ")
    .replaceAll("/", " ÷ ")
    .replaceAll("-", "−");
}

export function ResultPanel({
  calculation,
  busy,
}: {
  calculation: Calculation | null;
  busy: boolean;
}) {
  return (
    <section
      className="result-panel"
      aria-labelledby="result-title"
      aria-live="polite"
      aria-atomic="true"
      aria-busy={busy}
    >
      <div className="result-summary">
        <div className="result-label">
          <h2 id="result-title">Result</h2>
          {calculation && <p>{displayExpression(calculation.expression)}</p>}
        </div>
        <div
          className={`result-number ${calculation && calculation.result.length > 7 ? "long-result" : ""}`}
          data-testid="result"
          key={calculation?.result ?? "empty"}
        >
          {busy ? "…" : (calculation?.result ?? "—")}
        </div>
      </div>
      {calculation && (
        <div className="calculation-steps">
          <h3>Calculation steps</h3>
          {calculation.steps.length ? (
            <ol>
              {calculation.steps.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
          ) : (
            <p>{calculation.result}</p>
          )}
        </div>
      )}
    </section>
  );
}
