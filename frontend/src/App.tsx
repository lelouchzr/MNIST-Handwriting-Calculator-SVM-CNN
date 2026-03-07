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
} from "@phosphor-icons/react";
import { InkCanvas, downloadInk } from "./InkCanvas";
import { HistoryPanel } from "./components/HistoryPanel";
import { HelpDialog } from "./components/HelpDialog";
import { ResultPanel } from "./components/ResultPanel";
import { TokenReview } from "./components/TokenReview";
import { sampleExpression } from "./samples";
import { useWorkspace } from "./useWorkspace";

const operators = ["+", "−", "×", "÷", "(", ")", "."];

export default function App() {
  const workspace = useWorkspace();
  const [helpOpen, setHelpOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const history = useRef<HTMLElement>(null);
  const drawing = useRef<HTMLElement>(null);
  const { ink, expression, tokens, busy } = workspace;

  useEffect(() => {
    const onHelpKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.closest("input, textarea, dialog") || target.isContentEditable)
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

  function revealHistory() {
    setShowHistory(true);
    requestAnimationFrame(() => {
      history.current?.scrollIntoView({ behavior: "auto", block: "nearest" });
      history.current?.focus({ preventScroll: true });
    });
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
      <a href="#brouillon" className="skip-link">
        Aller au calcul
      </a>
      <header className="site-header">
        <a className="brand" href="#brouillon" aria-label="InkCalc, accueil">
          inkcalc<span aria-hidden="true">/</span>
        </a>
        <nav className="main-nav" aria-label="Navigation principale">
          <a className="active" href="#brouillon" aria-current="page">
            Brouillon
          </a>
          <button onClick={revealHistory}>Historique</button>
        </nav>
        <div className="header-utilities">
          <button className="help-trigger" onClick={() => setHelpOpen(true)}>
            Aide
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
            aria-label="Voir le projet InkCalc sur GitHub"
          >
            <GithubLogo size={25} weight="fill" />
          </a>
        </div>
      </header>
      <main id="brouillon" tabIndex={-1}>
        <div className="page-heading">
          <div>
            <p className="eyebrow">Calcul manuscrit</p>
            <h1>À main levée.</h1>
          </div>
          <p className="page-caption">Écrivez. Vérifiez. Calculez.</p>
        </div>
        <div className="workspace-layout">
          <div className="drawing-column">
            <section
              className="drawing-surface"
              aria-label="Brouillon manuscrit"
              ref={drawing}
            >
              <div
                className="drawing-toolbar"
                role="toolbar"
                aria-label="Outils du dessin"
              >
                <span className="pen-label">
                  <PencilSimple size={23} weight="regular" />
                  Stylo
                </span>
                <span
                  className="ink-swatch"
                  title="Encre noire"
                  aria-label="Encre noire"
                />
                <span className="toolbar-divider" />
                <button
                  className="icon-button"
                  disabled={!ink.past.length}
                  onClick={workspace.undo}
                  title="Annuler (Ctrl ou Cmd + Z)"
                  aria-label="Annuler le dernier trait"
                >
                  <ArrowCounterClockwise size={22} />
                </button>
                <button
                  className="icon-button"
                  disabled={!ink.future.length}
                  onClick={workspace.redo}
                  title="Rétablir (Ctrl ou Cmd + Maj + Z)"
                  aria-label="Rétablir le dernier trait"
                >
                  <ArrowClockwise size={22} />
                </button>
                <span className="toolbar-divider" />
                <button
                  className="icon-button"
                  disabled={!ink.strokes.length}
                  onClick={() => downloadInk(ink.strokes)}
                  title="Exporter le dessin en PNG"
                  aria-label="Exporter le dessin"
                >
                  <DownloadSimple size={22} />
                </button>
                <button
                  className="clear-button"
                  disabled={!ink.strokes.length && !expression}
                  onClick={() => workspace.changeInk([])}
                  title="Effacer le brouillon"
                  aria-label="Effacer le brouillon"
                >
                  <Trash size={20} />
                  <span>Effacer</span>
                </button>
              </div>
              <InkCanvas strokes={ink.strokes} onChange={workspace.changeInk} />
              <div className="canvas-caption">
                <span className="desktop-tip">
                  Une ligne. Un espace entre chaque symbole.
                </span>
                <span className="mobile-tip">Espacez les symboles.</span>
                <span className="stroke-count">
                  {ink.strokes.length}{" "}
                  {ink.strokes.length === 1 ? "trait" : "traits"}
                </span>
              </div>
              <div className="drawing-actions">
                <button className="example-button" onClick={loadExample}>
                  <span className="desktop-tip">Charger un exemple</span>
                  <span className="mobile-tip">Exemple</span>
                </button>
                <button
                  className="recognize-button"
                  disabled={!ink.strokes.length || busy !== null}
                  onClick={workspace.recognize}
                  aria-label="Reconnaître l’écriture"
                >
                  {busy === "recognize" ? "Lecture…" : "Reconnaître"}
                  <ArrowRight size={23} />
                </button>
              </div>
            </section>
            <section
              className="reading-section"
              aria-labelledby="reading-title"
            >
              <div className="section-heading">
                <h2 id="reading-title">Lecture</h2>
                <span>
                  {tokens.length
                    ? `${tokens.length} symboles`
                    : "Vérifiez avant de calculer"}
                </span>
              </div>
              <TokenReview tokens={tokens} onCorrect={workspace.correct} />
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
                    aria-label="Expression reconnue ou saisie au clavier"
                    value={expression}
                    placeholder="Ex. (12 + 7) × 2"
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
                    aria-label="Calculer"
                  >
                    <span>{busy === "calculate" ? "Calcul…" : "Calculer"}</span>
                    <ArrowRight size={23} />
                  </button>
                </div>
                <div className="operator-row" aria-label="Insérer un opérateur">
                  {operators.map((symbol) => (
                    <button
                      key={symbol}
                      type="button"
                      onClick={() => append(symbol)}
                      aria-label={`Insérer ${symbol}`}
                    >
                      {symbol}
                    </button>
                  ))}
                  <span>Modifiable au clavier.</span>
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
                  La reconnaissance est indisponible. Vous pouvez saisir votre
                  expression au clavier.
                </p>
              )}
            </section>
          </div>
          <aside className="result-column" aria-label="Résultat et historique">
            <ResultPanel
              calculation={workspace.calculation}
              busy={busy === "calculate"}
            />
            <HistoryPanel
              ref={history}
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
                Un doute sur un symbole ?<br />
                <span>Cliquez dessus pour le corriger.</span>
              </p>
            </button>
          </aside>
        </div>
      </main>
      <footer className="site-footer">
        <span>
          Calcul local <span aria-hidden="true">·</span> Aucun dessin conservé
        </span>
        <span className="footer-keyboard">
          <kbd>↵</kbd> Entrée pour calculer
        </span>
      </footer>
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
