import { useEffect, useReducer, useRef, useState } from "react";
import { request } from "./api";
import { readHistory, saveHistory } from "./history";
import { emptyInk, inkHistory } from "./inkHistory";
import type { Calculation, HistoryEntry, Stroke, Token } from "./types";

type Health = { recognition_ready: boolean; model_error: string | null };

function errorMessage(cause: unknown): string {
  if (cause instanceof Error) {
    if (cause.name === "TimeoutError")
      return "The service took too long to respond. Please try again.";
    if (cause instanceof TypeError)
      return "The calculation service is unreachable. Make sure it is running.";
    return cause.message;
  }
  return "Something went wrong. Please try again.";
}

export function useWorkspace() {
  const [ink, dispatch] = useReducer(inkHistory, emptyInk);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [expression, setExpression] = useState("");
  const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>(readHistory);
  const [busy, setBusy] = useState<"recognize" | "calculate" | null>(null);
  const [error, setError] = useState("");
  const [storageWarning, setStorageWarning] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const pending = useRef<AbortController | null>(null);
  const revision = useRef(0);

  useEffect(() => {
    setStorageWarning(!saveHistory(history));
  }, [history]);
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
  function resetReading() {
    invalidate();
    setTokens([]);
    setExpression("");
  }
  function changeInk(strokes: Stroke[]) {
    resetReading();
    dispatch({ type: "commit", strokes });
  }
  function undo() {
    if (!ink.past.length) return;
    resetReading();
    dispatch({ type: "undo" });
  }
  function redo() {
    if (!ink.future.length) return;
    resetReading();
    dispatch({ type: "redo" });
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.closest("input, textarea, dialog") || target.isContentEditable)
      )
        return;
      if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
      const key = event.key.toLowerCase();
      if (key === "z") {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
      } else if (key === "y" && event.ctrlKey) {
        event.preventDefault();
        redo();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  async function recognize() {
    if (!ink.strokes.length || busy) return;
    invalidate();
    const version = revision.current;
    const controller = new AbortController();
    pending.current = controller;
    setBusy("recognize");
    try {
      const result = await request<{ tokens: Token[]; expression: string }>(
        "recognize",
        { strokes: ink.strokes },
        AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
      );
      if (version !== revision.current) return;
      setTokens(result.tokens);
      setExpression(result.expression);
      setHealth({ recognition_ready: true, model_error: null });
    } catch (cause) {
      if (version === revision.current) setError(errorMessage(cause));
    } finally {
      if (version === revision.current) setBusy(null);
    }
  }
  async function calculate() {
    if (!expression.trim() || busy) return;
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
      setHistory((previous) => [entry, ...previous].slice(0, 20));
    } catch (cause) {
      if (version === revision.current) setError(errorMessage(cause));
    } finally {
      if (version === revision.current) setBusy(null);
    }
  }
  function editExpression(value: string) {
    invalidate();
    setTokens([]);
    setExpression(value.slice(0, 256));
  }
  function correct(index: number, label: string) {
    invalidate();
    const next = tokens.map((token, position) =>
      position === index ? { ...token, label, corrected: true } : token,
    );
    setTokens(next);
    setExpression(next.map((token) => token.label).join(""));
  }
  function restore(entry: HistoryEntry) {
    invalidate();
    setTokens([]);
    setExpression(entry.expression);
    setCalculation(entry);
  }

  return {
    ink,
    tokens,
    expression,
    calculation,
    history,
    busy,
    error,
    storageWarning,
    health,
    changeInk,
    undo,
    redo,
    recognize,
    calculate,
    editExpression,
    correct,
    restore,
    clearHistory: () => setHistory([]),
  };
}
