import type { Ref } from "react";
import { ArrowRight, ArrowUp } from "@phosphor-icons/react";
import type { HistoryEntry } from "../types";
import { displayExpression } from "./ResultPanel";

type Props = {
  ref: Ref<HTMLElement>;
  entries: HistoryEntry[];
  expanded: boolean;
  onExpand: () => void;
  onSelect: (entry: HistoryEntry) => void;
  onClear: () => void;
  storageWarning: boolean;
};

export function HistoryPanel({
  ref,
  entries,
  expanded,
  onExpand,
  onSelect,
  onClear,
  storageWarning,
}: Props) {
  const visible = expanded ? entries : entries.slice(0, 3);
  return (
    <section
      id="historique"
      ref={ref}
      className="history-panel"
      tabIndex={-1}
      aria-labelledby="history-title"
    >
      <div className="section-heading">
        <h2 id="history-title">Derniers calculs</h2>
        {entries.length > 3 && (
          <button
            className="text-button"
            onClick={onExpand}
            aria-expanded={expanded}
            aria-controls="history-entries"
          >
            {expanded ? "Réduire" : "Tout voir"}
            {expanded ? <ArrowUp size={16} /> : <ArrowRight size={16} />}
          </button>
        )}
      </div>
      {visible.length ? (
        <ol id="history-entries" className="history-list">
          {visible.map((entry) => (
            <li key={entry.id}>
              <button
                onClick={() => onSelect(entry)}
                aria-label={`Revoir ${displayExpression(entry.expression)}, résultat ${entry.result}`}
              >
                <span className="history-expression">
                  {displayExpression(entry.expression)}
                  <time dateTime={entry.createdAt}>
                    {new Date(entry.createdAt).toLocaleString("fr-FR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                </span>
                <strong>{entry.result}</strong>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <div className="history-empty">
          <p>Aucun calcul pour le moment.</p>
          <span>
            Vos 20 derniers résultats resteront
            <br />
            dans ce navigateur.
          </span>
        </div>
      )}
      {entries.length > 0 && (
        <div className="history-bottom">
          <span>{entries.length} / 20 conservés</span>
          <button className="text-button" onClick={onClear}>
            Vider l’historique
          </button>
        </div>
      )}
      {storageWarning && (
        <p className="service-note">
          Le navigateur ne permet pas d’enregistrer cet historique.
        </p>
      )}
    </section>
  );
}
