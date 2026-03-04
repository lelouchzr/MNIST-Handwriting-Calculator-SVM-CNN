import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowCounterClockwise,
  ArrowDown,
  Check,
  ClockCounterClockwise,
  DownloadSimple,
  Eraser,
  Info,
  PencilSimple,
  Plus,
  Sparkle,
  WarningCircle,
} from "@phosphor-icons/react";
import { InkCanvas, downloadInk } from "./InkCanvas";
import { request } from "./api";
import { readHistory, saveHistory } from "./history";
import { sampleExpression } from "./samples";
import type { Calculation, HistoryEntry, Stroke, Token } from "./types";

type Health = { recognition_ready: boolean; model_error: string | null };
const symbols = ["+", "−", "×", "÷", "(", ")", "."];

export default function App() {
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [expression, setExpression] = useState("");
  const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>(readHistory);
  const [busy, setBusy] = useState<"recognize" | "calculate" | null>(null);
  const [error, setError] = useState("");
  const [storageWarning, setStorageWarning] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const pending = useRef<AbortController | null>(null);
  const revision = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    request<Health>("health", undefined, controller.signal)
      .then(setHealth)
      .catch(() => {});
    return () => {
      controller.abort();
      pending.current?.abort();
    };
  }, []);

  function invalidate() {
    revision.current++;
    pending.current?.abort();
    setBusy(null);
    setError("");
    setCalculation(null);
  }

  function changeInk(next: Stroke[]) {
    invalidate();
    setStrokes(next);
    setTokens([]);
    setExpression("");
    setSelected(null);
  }

  useEffect(() => {
    const undo = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "z" &&
        !(event.target instanceof HTMLInputElement)
      ) {
        event.preventDefault();
        changeInk(strokes.slice(0, -1));
      }
    };
    window.addEventListener("keydown", undo);
    return () => window.removeEventListener("keydown", undo);
  });

  async function recognize() {
    invalidate();
    const version = revision.current;
    const controller = new AbortController();
    pending.current = controller;
    setBusy("recognize");
    try {
      const result = await request<{ tokens: Token[]; expression: string }>(
        "recognize",
        { strokes },
        AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
      );
      if (version !== revision.current) return;
      setTokens(result.tokens);
      setExpression(result.expression);
      setHealth({ recognition_ready: true, model_error: null });
    } catch (cause) {
      if (version === revision.current)
        setError(
          cause instanceof Error
            ? cause.message
            : "Reconnaissance indisponible.",
        );
    } finally {
      if (version === revision.current) setBusy(null);
    }
  }

  async function calculate() {
    invalidate();
    const version = revision.current;
    const controller = new AbortController();
    pending.current = controller;
    setBusy("calculate");
    try {
      const result = await request<Calculation>(
        "calculate",
        { expression },
        AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
      );
      if (version !== revision.current) return;
      setCalculation(result);
      const entry: HistoryEntry = {
        ...result,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
      };
      setHistory((previous) => {
        const next = [entry, ...previous].slice(0, 20);
        setStorageWarning(!saveHistory(next));
        return next;
      });
    } catch (cause) {
      if (version === revision.current)
        setError(
          cause instanceof Error ? cause.message : "Calcul indisponible.",
        );
    } finally {
      if (version === revision.current) setBusy(null);
    }
  }

  function correct(index: number, label: string) {
    invalidate();
    const next = tokens.map((token, position) =>
      position === index ? { ...token, label } : token,
    );
    setTokens(next);
    setExpression(next.map((token) => token.label).join(""));
    setSelected(null);
  }

  function append(symbol: string) {
    invalidate();
    setTokens([]);
    setSelected(null);
    const field = input.current;
    const start = field?.selectionStart ?? expression.length;
    const end = field?.selectionEnd ?? start;
    setExpression(expression.slice(0, start) + symbol + expression.slice(end));
    field?.focus();
    requestAnimationFrame(() =>
      field?.setSelectionRange(start + symbol.length, start + symbol.length),
    );
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="InkCalc, accueil">
          <span className="brand-mark">
            <PencilSimple weight="bold" size={23} />
          </span>
          inkcalc<span className="brand-period">.</span>
        </a>
        <span className="header-caption">
          LES IDÉES COMMENCENT SUR LE PAPIER.
        </span>
        <a
          className="header-link"
          href="https://github.com/lelouchzr/inkcalc"
          target="_blank"
          rel="noreferrer"
        >
          Le projet <ArrowRight size={16} />
        </a>
      </header>

      <main>
        <section className="intro">
          <div>
            <div className="eyebrow">
              <span /> LE CALCUL, À MAIN LEVÉE
            </div>
            <h1>
              Posez vos chiffres.
              <br />
              <span>Gardez le fil.</span>
            </h1>
            <p>
              Écrivez une opération, vérifiez la lecture, laissez le calcul se
              faire.
            </p>
          </div>
          <div className="intro-note">
            <span className="note-number">01 — 02 — 03</span>
            <p>
              Une feuille pour réfléchir.
              <br />
              Un coup de main pour calculer.
            </p>
            <span className="note-rule" />
          </div>
        </section>

        <div className="workspace-layout">
          <section className="workspace" aria-label="Atelier de calcul">
            <div className="workspace-top">
              <div className="workspace-title">
                <PencilSimple size={18} weight="bold" /> Votre brouillon
              </div>
              <span className="local-badge">
                <span /> Traitement local
              </span>
            </div>
            <div className="toolbar">
              <div className="tool-group">
                <span className="pen-indicator" />
                <span>Stylo</span>
                <span className="toolbar-divider" />
                <span className="ink-label">Encre verte</span>
              </div>
              <div className="tool-group">
                <button
                  className="icon-button"
                  title="Annuler le dernier trait (Ctrl ou Cmd + Z)"
                  aria-label="Annuler le dernier trait"
                  disabled={!strokes.length}
                  onClick={() => changeInk(strokes.slice(0, -1))}
                >
                  <ArrowCounterClockwise size={19} />
                </button>
                <button
                  className="icon-button"
                  title="Exporter le dessin en PNG"
                  aria-label="Exporter le dessin"
                  disabled={!strokes.length}
                  onClick={() => downloadInk(strokes)}
                >
                  <DownloadSimple size={19} />
                </button>
                <span className="toolbar-divider" />
                <button
                  className="text-button clear-button"
                  disabled={!strokes.length && !expression}
                  onClick={() => changeInk([])}
                >
                  <Eraser size={17} /> Effacer
                </button>
              </div>
            </div>
            <InkCanvas strokes={strokes} onChange={changeInk} />
            <div className="canvas-footer">
              <span>Un symbole à la fois. Un peu d’espace entre chacun.</span>
              <span className="mono">
                {String(strokes.length).padStart(2, "0")} TRAITS
              </span>
            </div>
            <div className="recognize-row">
              <button
                className="text-button example-button"
                onClick={() => changeInk(sampleExpression())}
              >
                <Plus size={16} /> Essayer un exemple
              </button>
              <button
                className="primary-button"
                onClick={recognize}
                disabled={!strokes.length || busy !== null}
              >
                {busy === "recognize"
                  ? "Lecture en cours…"
                  : "Lire mon écriture"}
                <Sparkle size={18} weight="bold" />
              </button>
            </div>

            <div className="reading-section">
              <div className="section-heading">
                <span className="step-label">02</span>
                <h2>Vérifiez la lecture</h2>
                <span className="section-hint">Vous gardez la main.</span>
              </div>
              {tokens.length > 0 && (
                <>
                  <div className="token-list" aria-label="Symboles reconnus">
                    {tokens.map((token, index) => (
                      <div className="token-item" key={index}>
                        <button
                          className={`token ${selected === index ? "selected" : ""}`}
                          onClick={() =>
                            setSelected(selected === index ? null : index)
                          }
                          aria-expanded={selected === index}
                          aria-label={`Corriger le symbole ${index + 1} : ${token.label}`}
                        >
                          <img src={token.thumbnail} alt="" />
                          <strong>{token.label}</strong>
                          <span
                            className={
                              token.confidence < 0.65 ? "uncertain" : ""
                            }
                          >
                            {Math.round(token.confidence * 100)} %
                          </span>
                        </button>
                      </div>
                    ))}
                  </div>
                  {selected !== null && (
                    <div className="correction-row">
                      <span>Remplacer « {tokens[selected].label} » par</span>
                      {[
                        ...new Set([
                          ...tokens[selected].alternatives.map(
                            (item) => item.label,
                          ),
                          ..."0123456789",
                          ...symbols,
                        ]),
                      ].map((label) => (
                        <button
                          key={label}
                          onClick={() => correct(selected, label)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  )}
                  <p className="prediction-note">
                    Scores du modèle, sans garantie de lecture. Cliquez sur un
                    symbole pour le corriger.
                  </p>
                </>
              )}
              <label className="expression-label" htmlFor="expression">
                Expression reconnue ou saisie au clavier
              </label>
              <div className="expression-field">
                <span aria-hidden="true">ƒ</span>
                <input
                  ref={input}
                  id="expression"
                  value={expression}
                  placeholder="Ex. (12 + 7) × 2"
                  maxLength={256}
                  autoComplete="off"
                  spellCheck={false}
                  onChange={(event) => {
                    invalidate();
                    setExpression(event.target.value);
                    setTokens([]);
                    setSelected(null);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && expression.trim() && !busy)
                      void calculate();
                  }}
                />
                <kbd>↵</kbd>
              </div>
              <div className="expression-actions">
                <div className="symbol-pad" aria-label="Insérer un opérateur">
                  {symbols.map((symbol) => (
                    <button
                      key={symbol}
                      aria-label={`Insérer ${symbol}`}
                      onClick={() => append(symbol)}
                    >
                      {symbol}
                    </button>
                  ))}
                </div>
                <button
                  className="calculate-button"
                  onClick={calculate}
                  disabled={!expression.trim() || busy !== null}
                >
                  {busy === "calculate" ? "Calcul…" : "Calculer"}
                  <ArrowRight size={18} />
                </button>
              </div>
              {error && (
                <div className="error-message" role="alert">
                  <WarningCircle size={19} />
                  <span>
                    {error.includes("fetch")
                      ? "Le service Python est injoignable. Vérifiez qu’il est démarré."
                      : error}
                  </span>
                </div>
              )}
              {health && !health.recognition_ready && (
                <p className="model-warning">
                  La reconnaissance est indisponible. La saisie au clavier reste
                  accessible.
                </p>
              )}
            </div>
          </section>

          <aside className="results-column">
            <section
              className={`result-panel ${calculation ? "has-result" : ""}`}
              aria-label="Résultat"
              aria-live="polite"
            >
              <div className="section-heading">
                <span className="step-label">03</span>
                <h2>Le résultat</h2>
                {calculation && <Check size={18} />}
              </div>
              <div className="result-expression">
                {calculation
                  ? calculation.expression
                      .replaceAll("*", " × ")
                      .replaceAll("/", " ÷ ")
                  : "Votre prochain résultat."}
              </div>
              <div className="result-number" data-testid="result">
                {calculation?.result ?? "—"}
              </div>
              {calculation ? (
                <div className="calculation-steps">
                  <span className="mini-label">LE CHEMIN DU CALCUL</span>
                  {calculation.steps.length ? (
                    calculation.steps.map((step, index) => (
                      <p key={index}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        {step}
                      </p>
                    ))
                  ) : (
                    <p>Un nombre, tout simplement.</p>
                  )}
                </div>
              ) : (
                <p className="result-empty">
                  Vos opérations et leurs étapes
                  <br />
                  prendront place ici.
                </p>
              )}
            </section>
            <section className="history-panel">
              <div className="history-heading">
                <h2>
                  <ClockCounterClockwise size={18} /> Derniers calculs
                </h2>
                {history.length > 0 && (
                  <button
                    className="text-button"
                    onClick={() => {
                      setHistory([]);
                      setStorageWarning(!saveHistory([]));
                    }}
                  >
                    Vider
                  </button>
                )}
              </div>
              {history.length ? (
                <ol className="history-list">
                  {history.map((entry) => (
                    <li key={entry.id}>
                      <button
                        onClick={() => {
                          invalidate();
                          setExpression(entry.expression);
                          setTokens([]);
                          setSelected(null);
                          input.current?.focus();
                        }}
                      >
                        <span>
                          {entry.expression
                            .replaceAll("*", "×")
                            .replaceAll("/", "÷")}
                          <small>
                            {new Date(entry.createdAt).toLocaleTimeString(
                              "fr-FR",
                              { hour: "2-digit", minute: "2-digit" },
                            )}
                          </small>
                        </span>
                        <strong>{entry.result}</strong>
                      </button>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="history-empty">
                  <span className="history-line" />
                  <p>Une page encore blanche.</p>
                  <small>
                    Vos 20 derniers calculs restent
                    <br />
                    dans ce navigateur.
                  </small>
                </div>
              )}
              {storageWarning && (
                <p className="model-warning">
                  Le navigateur ne permet pas d’enregistrer cet historique.
                </p>
              )}
            </section>
            <details className="help">
              <summary>
                <Info size={17} /> Quelques repères <Plus size={15} />
              </summary>
              <div>
                <p>
                  Écrivez sur une seule ligne, sans superposer les symboles.
                  Dessinez × avec deux diagonales et ÷ avec une barre et deux
                  points.
                </p>
                <p>
                  Les chiffres et + − × ÷ ( ) sont reconnus. Les décimales se
                  corrigent aussi au clavier. Une virgule est acceptée dans
                  l’expression.
                </p>
                <p>
                  Le modèle peut se tromper, surtout sur les opérateurs.
                  Vérifiez la lecture avant de calculer.
                </p>
              </div>
            </details>
          </aside>
        </div>

        <section className="how-it-works" aria-label="Comment ça marche">
          <div>
            <span className="mini-label">DU TRAIT AU RÉSULTAT</span>
            <h2>
              Simple en surface.
              <br />
              Précis dans le détail.
            </h2>
          </div>
          <div className="how-step">
            <span>
              01 <ArrowDown size={16} />
            </span>
            <h3>Écrivez librement</h3>
            <p>
              À la souris, au doigt ou au stylet.
              <br />
              Votre brouillon reste votre brouillon.
            </p>
          </div>
          <div className="how-step">
            <span>
              02 <ArrowDown size={16} />
            </span>
            <h3>Relisez ensemble</h3>
            <p>
              Un modèle entraîné sur MNIST.
              <br />
              Chaque symbole reste modifiable.
            </p>
          </div>
          <div className="how-step">
            <span>
              03 <Check size={16} />
            </span>
            <h3>Suivez le calcul</h3>
            <p>
              Les priorités sont respectées.
              <br />
              Les étapes restent visibles.
            </p>
          </div>
        </section>
      </main>
      <footer className="site-footer">
        <span>
          inkcalc. <span>Moins de touches. Plus d’idées.</span>
        </span>
        <span>
          Python + React <span className="footer-dot">·</span> Données dans
          votre navigateur
        </span>
      </footer>
    </div>
  );
}
