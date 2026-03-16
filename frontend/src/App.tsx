import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowCounterClockwise,
  ArrowClockwise,
  DownloadSimple,
  Trash,
  GithubLogo,
  PencilSimple,
  WarningCircle,
  MagnifyingGlass,
} from "@phosphor-icons/react";
import { InkCanvas, downloadInk } from "./InkCanvas";
import { HistoryPanel } from "./components/HistoryPanel";
import { HelpDialog } from "./components/HelpDialog";
import { ResultPanel } from "./components/ResultPanel";
import { TokenReview } from "./components/TokenReview";
import { RecognitionInspector } from "./components/RecognitionInspector";
import { ModelComparison } from "./components/ModelComparison";
import { sampleExpression, challengingDigit } from "./samples";
import { useWorkspace } from "./useWorkspace";

const operators = ["+", "−", "×", "÷", "(", ")", "."];

export default function App() {
  const workspace = useWorkspace();
  const [helpOpen, setHelpOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [inspected, setInspected] = useState<number | null>(null);
  const [showSegmentation, setShowSegmentation] = useState(true);
  const inspectButton = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const drawing = useRef<HTMLElement>(null);
  const { ink, expression, tokens, busy } = workspace;

  useEffect(() => {
    if (!tokens.length) setInspected(null);
    else if (inspected !== null && inspected >= tokens.length) setInspected(0);
  }, [tokens, inspected]);

  function openInspector(index: number) {
    setInspected(index);
    requestAnimationFrame(() => {
      const panel = document.getElementById("recognition-inspector");
      panel?.scrollIntoView({ block: "nearest" });
      panel?.focus({ preventScroll: true });
    });
  }

  function closeInspector() {
    setInspected(null);
    inspectButton.current?.focus({ preventScroll: true });
  }

  useEffect(() => {
    const onHelpKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.closest("input, textarea, select, dialog") ||
          target.isContentEditable)
      )
        return;
      if (
        event.key === "?" &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey
      ) {
        event.preventDefault();
        setHelpOpen(true);
      }
    };
    window.addEventListener("keydown", onHelpKey);
    return () => window.removeEventListener("keydown", onHelpKey);
  }, []);

  function loadExample() {
    const bounds = drawing.current
      ?.querySelector("canvas")
      ?.getBoundingClientRect();
    workspace.changeInk(
      sampleExpression(bounds ? (1000 * bounds.height) / bounds.width : 360),
    );
  }

  function loadChallenge() {
    const bounds = drawing.current
      ?.querySelector("canvas")
      ?.getBoundingClientRect();
    workspace.changeInk(
      challengingDigit(bounds ? (1000 * bounds.height) / bounds.width : 360),
    );
  }

  function append(symbol: string) {
    const start = input.current?.selectionStart ?? expression.length;
    const end = input.current?.selectionEnd ?? start;
    const next = (
      expression.slice(0, start) +
      symbol +
      expression.slice(end)
    ).slice(0, 256);
    workspace.editExpression(next);
    input.current?.focus();
    requestAnimationFrame(() =>
      input.current?.setSelectionRange(
        Math.min(next.length, start + symbol.length),
        Math.min(next.length, start + symbol.length),
      ),
    );
  }

  return (
    <div className="app-shell">
      <a href="#workspace" className="skip-link">
        Skip to calculator
      </a>
      <header className="site-header">
        <a className="brand" href="#workspace" aria-label="InkCalc home">
          inkcalc<span aria-hidden="true">/</span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          <a className="active" href="#workspace" aria-current="page">
            Workspace
          </a>
        </nav>
        <div className="header-utilities">
          <button className="help-trigger" onClick={() => setHelpOpen(true)}>
            Help
            <span className="shortcut" aria-hidden="true">
              ?
            </span>
          </button>
          <span className="utility-divider" />
          <a
            className="github-link"
            href="https://github.com/lelouchzr/inkcalc"
            target="_blank"
            rel="noreferrer"
            aria-label="View InkCalc on GitHub"
          >
            <GithubLogo size={25} weight="fill" />
          </a>
        </div>
      </header>
      <main id="workspace" tabIndex={-1}>
        <div className="page-heading">
          <div>
            <p className="eyebrow">Handwritten math</p>
            <h1>By hand.</h1>
          </div>
          <p className="page-caption">Write. Check. Calculate.</p>
        </div>
        <div className="model-controls">
          <fieldset className="model-switch">
            <legend>Recognition model</legend>
            {(["svm", "cnn", "compare"] as const).map((mode) => (
              <label key={mode}>
                <input
                  type="radio"
                  name="recognition-model"
                  value={mode}
                  checked={workspace.mode === mode}
                  onChange={() => workspace.changeMode(mode)}
                  disabled={
                    mode === "compare"
                      ? workspace.health?.models.svm?.ready === false ||
                        workspace.health?.models.cnn?.ready === false
                      : workspace.health?.models[mode]?.ready === false
                  }
                />
                <span>
                  {mode === "compare" ? "Compare" : mode.toUpperCase()}
                </span>
              </label>
            ))}
          </fieldset>
          <p>
            {workspace.mode === "compare"
              ? "One drawing. Both models. Inspect agreements and differences."
              : workspace.mode === "cnn"
                ? "CNN · uncalibrated softmax scores"
                : "HOG + SVM · calibrated probabilities"}
            {workspace.mode === "compare" && (
              <button className="challenge-button" onClick={loadChallenge}>
                Load synthetic challenge
              </button>
            )}
          </p>
        </div>
        <div className="workspace-layout">
          <div className="drawing-column">
            <section
              className="drawing-surface"
              aria-label="Handwriting canvas"
              ref={drawing}
            >
              <div
                className="drawing-toolbar"
                role="toolbar"
                aria-label="Drawing tools"
              >
                <span className="pen-label">
                  <PencilSimple size={23} weight="regular" />
                  Pen
                </span>
                <span
                  className="ink-swatch"
                  title="Black ink"
                  aria-label="Black ink"
                />
                <span className="toolbar-divider" />
                <button
                  className="icon-button"
                  disabled={!ink.past.length}
                  onClick={workspace.undo}
                  title="Undo (Ctrl or Cmd + Z)"
                  aria-label="Undo the last drawing action"
                >
                  <ArrowCounterClockwise size={22} />
                </button>
                <button
                  className="icon-button"
                  disabled={!ink.future.length}
                  onClick={workspace.redo}
                  title="Redo (Ctrl or Cmd + Shift + Z)"
                  aria-label="Redo the last drawing action"
                >
                  <ArrowClockwise size={22} />
                </button>
                <span className="toolbar-divider" />
                <button
                  className="icon-button"
                  disabled={!ink.strokes.length}
                  onClick={() => downloadInk(ink.strokes)}
                  title="Export drawing as PNG"
                  aria-label="Export drawing"
                >
                  <DownloadSimple size={22} />
                </button>
                <button
                  className="clear-button"
                  disabled={!ink.strokes.length && !expression}
                  onClick={() => workspace.changeInk([])}
                  title="Clear drawing"
                  aria-label="Clear drawing"
                >
                  <Trash size={20} />
                  <span>Clear</span>
                </button>
              </div>
              <InkCanvas
                strokes={ink.strokes}
                onChange={workspace.changeInk}
                onDrawStart={workspace.beginStroke}
                tokens={tokens}
                selectedIndex={inspected}
                showSegmentation={showSegmentation}
                onInspect={openInspector}
              />
              <div className="canvas-caption">
                <span className="desktop-tip">
                  One line. Leave a gap between symbols.
                </span>
                <span className="mobile-tip">Space out your symbols.</span>
                {tokens.length > 0 && (
                  <label className="segmentation-toggle">
                    <input
                      type="checkbox"
                      checked={showSegmentation}
                      onChange={(event) =>
                        setShowSegmentation(event.target.checked)
                      }
                    />
                    Segments
                  </label>
                )}
                <span className="stroke-count">
                  {ink.strokes.length}{" "}
                  {ink.strokes.length === 1 ? "stroke" : "strokes"}
                </span>
              </div>
              <div className="drawing-actions">
                <button className="example-button" onClick={loadExample}>
                  <span className="desktop-tip">Load an example</span>
                  <span className="mobile-tip">Example</span>
                </button>
                <button
                  className="recognize-button"
                  disabled={!ink.strokes.length || busy !== null}
                  onClick={workspace.recognize}
                  aria-label="Recognize handwriting"
                >
                  {busy === "recognize" ? "Reading…" : "Recognize"}
                  <ArrowRight size={23} />
                </button>
              </div>
            </section>
            <section
              className="reading-section"
              aria-labelledby="reading-title"
            >
              <div className="section-heading">
                <h2 id="reading-title">Recognition</h2>
                <div className="recognition-actions">
                  <span>
                    {tokens.length
                      ? `${tokens.length} ${tokens.length === 1 ? "symbol" : "symbols"}`
                      : "Check before calculating"}
                  </span>
                  <button
                    className="inspect-trigger"
                    ref={inspectButton}
                    disabled={!tokens.length}
                    onClick={() => openInspector(inspected ?? 0)}
                    aria-expanded={inspected !== null}
                    aria-controls="recognition-inspector"
                    title={
                      tokens.length
                        ? "Inspect recognition details"
                        : "Recognize handwriting to inspect its symbols"
                    }
                  >
                    <MagnifyingGlass size={17} />
                    Inspect
                  </button>
                </div>
              </div>
              <TokenReview
                tokens={tokens}
                onCorrect={workspace.correct}
                inspectedIndex={inspected}
              />
              <form
                className="expression-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void workspace.calculate();
                }}
              >
                <label htmlFor="expression">Expression</label>
                <div className="expression-row">
                  <input
                    id="expression"
                    ref={input}
                    aria-label="Recognized or typed expression"
                    value={expression}
                    placeholder="e.g. (12 + 7) × 2"
                    maxLength={256}
                    autoComplete="off"
                    spellCheck={false}
                    onChange={(event) =>
                      workspace.editExpression(event.target.value)
                    }
                  />
                  <button
                    className="calculate-button"
                    type="submit"
                    disabled={!expression.trim() || busy !== null}
                    aria-label="Calculate"
                  >
                    <span>
                      {busy === "calculate" ? "Calculating…" : "Calculate"}
                    </span>
                    <ArrowRight size={23} />
                  </button>
                </div>
                <div className="operator-row" aria-label="Insert an operator">
                  {operators.map((symbol) => (
                    <button
                      key={symbol}
                      type="button"
                      onClick={() => append(symbol)}
                      aria-label={`Insert ${symbol}`}
                    >
                      {symbol}
                    </button>
                  ))}
                  <span>Editable with your keyboard.</span>
                </div>
              </form>
              {workspace.error && (
                <div className="error-message" role="alert">
                  <WarningCircle size={21} />
                  <p>{workspace.error}</p>
                </div>
              )}
              {workspace.health && !workspace.health.recognition_ready && (
                <p className="service-note">
                  Recognition is unavailable. You can still type your
                  expression.
                </p>
              )}
            </section>
          </div>
          <aside className="result-column" aria-label="Result and history">
            {workspace.mode !== "compare" &&
              inspected !== null &&
              tokens[inspected] && (
                <RecognitionInspector
                  tokens={tokens}
                  index={inspected}
                  strokes={ink.strokes}
                  onSelect={setInspected}
                  onClose={closeInspector}
                />
              )}
            <ResultPanel
              calculation={workspace.calculation}
              busy={busy === "calculate"}
            />
            <HistoryPanel
              entries={workspace.history}
              expanded={showHistory}
              onExpand={() => setShowHistory(!showHistory)}
              onSelect={workspace.restore}
              onClear={workspace.clearHistory}
              storageWarning={workspace.storageWarning}
            />
            <button
              className="correction-tip"
              onClick={() => setHelpOpen(true)}
            >
              <span aria-hidden="true">i</span>
              <p>
                Unsure about a symbol?
                <br />
                <span>Click it to correct it.</span>
              </p>
            </button>
          </aside>
          {workspace.mode === "compare" && tokens.length > 0 && (
            <ModelComparison
              tokens={tokens}
              strokes={ink.strokes}
              index={inspected}
              onSelect={openInspector}
              onClose={closeInspector}
              source={workspace.expressionSource}
              onUseModel={workspace.useModelExpression}
              health={workspace.health}
            />
          )}
        </div>
      </main>
      <footer className="site-footer">
        <span>
          Calculated locally <span aria-hidden="true">·</span> No drawings saved
        </span>
        <span className="footer-keyboard">
          <kbd>↵</kbd> Press Enter to calculate
        </span>
      </footer>
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
