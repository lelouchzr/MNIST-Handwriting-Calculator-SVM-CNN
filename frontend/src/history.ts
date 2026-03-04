import type { HistoryEntry } from "./types";

export const HISTORY_KEY = "inkcalc.history.v1";

export function readHistory(): HistoryEntry[] {
  try {
    const parsed: unknown = JSON.parse(
      localStorage.getItem(HISTORY_KEY) ?? "[]",
    );
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (entry): entry is HistoryEntry =>
          entry !== null &&
          typeof entry === "object" &&
          typeof entry.id === "string" &&
          typeof entry.expression === "string" &&
          typeof entry.result === "string" &&
          typeof entry.createdAt === "string" &&
          Number.isFinite(Date.parse(entry.createdAt)) &&
          Array.isArray(entry.steps) &&
          entry.steps.every((step: unknown) => typeof step === "string"),
      )
      .slice(0, 20);
  } catch {
    return [];
  }
}

export function saveHistory(entries: HistoryEntry[]): boolean {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 20)));
    return true;
  } catch {
    return false; // Private browsing or a full quota must not prevent calculation.
  }
}
