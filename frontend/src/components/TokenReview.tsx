import { useEffect, useRef, useState } from "react";
import { X } from "@phosphor-icons/react";
import type { Token } from "../types";

type Props = {
  tokens: Token[];
  onCorrect: (index: number, label: string) => void;
};

export function TokenReview({ tokens, onCorrect }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const choices = useRef<HTMLDivElement>(null);
  const active = selected === null ? null : tokens[selected];
  useEffect(() => {
    setSelected(null);
  }, [tokens]);
  useEffect(() => {
    if (active)
      choices.current
        ?.querySelector<HTMLButtonElement>("button[data-choice]")
        ?.focus();
  }, [active]);
  function close() {
    if (selected !== null) buttons.current[selected]?.focus();
    setSelected(null);
  }
  if (!tokens.length)
    return (
      <div className="reading-empty">
        <span aria-hidden="true">—</span>
        <p>Votre écriture apparaîtra ici, symbole par symbole.</p>
      </div>
    );
  return (
    <>
      <div className="token-list" aria-label="Symboles reconnus">
        {tokens.map((token, index) => (
          <button
            key={index}
            ref={(element) => {
              buttons.current[index] = element;
            }}
            className={`token ${selected === index ? "is-selected" : ""}`}
            onClick={() => setSelected(selected === index ? null : index)}
            aria-expanded={selected === index}
            aria-controls="symbol-correction"
            aria-label={`Corriger le symbole ${index + 1} : ${token.label}`}
          >
            <span className="token-drawing">
              <img src={token.thumbnail} alt="" />
            </span>
            <strong>{token.label}</strong>
            <span
              className={
                !token.corrected && token.confidence < 0.65 ? "uncertain" : ""
              }
            >
              {token.corrected
                ? "corrigé"
                : `${Math.round(token.confidence * 100)} %`}
            </span>
          </button>
        ))}
      </div>
      <p className="reading-hint">
        Cliquez sur un symbole pour le corriger. Les scores restent indicatifs.
      </p>
      {active && selected !== null && (
        <div
          id="symbol-correction"
          className="symbol-correction"
          ref={choices}
          role="group"
          aria-label={`Remplacer le symbole ${active.label}`}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.stopPropagation();
              close();
            }
          }}
        >
          <div className="correction-heading">
            <p>
              Remplacer <strong>{active.label}</strong> par
            </p>
            <button
              className="icon-button"
              onClick={close}
              aria-label="Fermer la correction"
            >
              <X size={18} />
            </button>
          </div>
          <div className="correction-choices">
            {[
              ...new Set([
                ...active.alternatives.map((item) => item.label),
                ..."0123456789",
                "+",
                "−",
                "×",
                "÷",
                "(",
                ")",
                ".",
              ]),
            ].map((label) => (
              <button
                data-choice
                key={label}
                onClick={() => {
                  onCorrect(selected, label);
                  close();
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
