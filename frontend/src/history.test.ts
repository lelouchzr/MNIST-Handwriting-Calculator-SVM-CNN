import { beforeEach, describe, expect, it, vi } from "vitest";
import { HISTORY_KEY, readHistory, saveHistory } from "./history";
import type { HistoryEntry } from "./types";

const entry: HistoryEntry = {
  id: "calculation-1",
  createdAt: "2026-10-29T10:00:00Z",
  expression: "2+3",
  result: "5",
  steps: ["2 + 3 = 5"],
};

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  });
});

describe("persistent calculation history", () => {
  it("restores calculations after a page reload", () => {
    expect(saveHistory([entry])).toBe(true);
    expect(readHistory()).toEqual([entry]);
  });
  it("recovers from invalid JSON without breaking the workspace", () => {
    localStorage.setItem(HISTORY_KEY, "{broken");
    expect(readHistory()).toEqual([]);
  });
  it("filters malformed entries and invalid dates", () => {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify([
        null,
        "wrong",
        { ...entry, steps: [42] },
        { ...entry, createdAt: "yesterday" },
        entry,
      ]),
    );
    expect(readHistory()).toEqual([entry]);
  });
  it("keeps only twenty entries", () => {
    saveHistory(
      Array.from({ length: 25 }, (_, i) => ({ ...entry, id: String(i) })),
    );
    expect(readHistory()).toHaveLength(20);
    expect(readHistory()[0].id).toBe("0");
  });
  it("remains usable if browser storage is unavailable", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("access denied");
      },
      setItem: () => {
        throw new Error("quota exceeded");
      },
    });
    expect(readHistory()).toEqual([]);
    expect(saveHistory([entry])).toBe(false);
  });
  it("clears persisted calculations", () => {
    saveHistory([entry]);
    saveHistory([]);
    expect(readHistory()).toEqual([]);
  });
});
