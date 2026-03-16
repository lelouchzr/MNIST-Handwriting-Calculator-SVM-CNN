import { ArrowRight, ArrowUp } from "@phosphor-icons/react";
import type { HistoryEntry } from "../types";
import { displayExpression } from "./ResultPanel";

type Props = {
  entries: HistoryEntry[];
  expanded: boolean;
  onExpand: () => void;
  onSelect: (entry: HistoryEntry) => void;
  onClear: () => void;
  storageWarning: boolean;
};

export function HistoryPanel({
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
      id="history"
      className="history-panel"
      tabIndex={-1}
      aria-labelledby="history-title"
    >
      <div className="section-heading">
        <h2 id="history-title">Recent calculations</h2>
        {entries.length > 3 && (
          <button
            className="text-button"
            onClick={onExpand}
            aria-expanded={expanded}
            aria-controls="history-entries"
          >
            {expanded ? "Show less" : "View all"}
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
                aria-label={`Review ${displayExpression(entry.expression)}, result ${entry.result}`}
              >
                <span className="history-expression">
                  {displayExpression(entry.expression)}
                  <time dateTime={entry.createdAt}>
                    {new Date(entry.createdAt).toLocaleString("en-GB", {
                      day: "2-digit",
                      month: "short",
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
          <p>No calculations yet.</p>
          <span>
            Your last 20 results will stay
            <br />
            in this browser.
          </span>
        </div>
      )}
      {entries.length > 0 && (
        <div className="history-bottom">
          <span>{entries.length} / 20 saved</span>
          <button className="text-button" onClick={onClear}>
            Clear history
          </button>
        </div>
      )}
      {storageWarning && (
        <p className="service-note">Your browser cannot save this history.</p>
      )}
    </section>
  );
}
