// @vitest-environment jsdom
import { useRef, useState } from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { InspectorShell } from "./InspectorShell";
import { InspectionTabs } from "./InspectionTabs";
import type { InspectionTab } from "./InspectionTabs";

let mobile = false;
const listeners = new Set<() => void>();
const symbols = [{ label: "1" }, { label: "2" }];

function Harness() {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [tab, setTab] = useState<InspectionTab>("Input");
  const opener = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button ref={opener} onClick={() => setOpen(true)}>
        Inspect drawing
      </button>
      <button>Draw outside the inspector</button>
      <InspectorShell
        open={open}
        tokens={symbols}
        index={index}
        onSelect={setIndex}
        onClose={() => setOpen(false)}
        returnFocus={opener}
        comparison
      >
        <InspectionTabs value={tab} onChange={setTab}>
          <p>
            {tab} for symbol {index + 1}
          </p>
        </InspectionTabs>
      </InspectorShell>
    </>
  );
}

beforeEach(() => {
  mobile = false;
  listeners.clear();
  vi.stubGlobal("matchMedia", () => ({
    get matches() {
      return mobile;
    },
    addEventListener: (_: string, listener: () => void) =>
      listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) =>
      listeners.delete(listener),
  }));
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function openInspector() {
  const user = userEvent.setup();
  render(<Harness />);
  const opener = screen.getByRole("button", { name: "Inspect drawing" });
  await user.click(opener);
  const dialog = await screen.findByRole("dialog", { name: "Inspect" });
  await waitFor(() => expect(document.activeElement).toBe(dialog));
  return { user, opener, dialog };
}

describe("responsive inspection interactions", () => {
  it("dismisses the mobile panel on a backdrop press and restores its opener", async () => {
    mobile = true;
    const { user, opener } = await openInspector();
    await user.click(document.querySelector(".inspection-backdrop")!);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });
  it("keeps desktop drawing controls available and restores focus on Escape", async () => {
    const { user, opener, dialog } = await openInspector();
    const outside = screen.getByRole("button", {
      name: "Draw outside the inspector",
    });
    await user.click(outside);
    expect(screen.getByRole("dialog", { name: "Inspect" })).toBe(dialog);
    expect(document.activeElement).toBe(outside);
    await user.click(screen.getByRole("tab", { name: "Input" }));
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });

  it("makes mobile inspection modal and keeps keyboard focus inside", async () => {
    mobile = true;
    const { user, dialog, opener } = await openInspector();
    expect(
      screen.queryByRole("button", { name: "Draw outside the inspector" }),
    ).toBeNull();
    await user.tab({ shift: true });
    await waitFor(() =>
      expect(dialog.contains(document.activeElement)).toBe(true),
    );
    await user.click(screen.getByRole("button", { name: "Close inspector" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });

  it("uses arrow/Home/End navigation and updates the selected symbol", async () => {
    const { user } = await openInspector();
    const previous = screen.getByRole("button", { name: "Previous symbol" });
    expect((previous as HTMLButtonElement).disabled).toBe(true);
    await user.click(screen.getByRole("button", { name: "Next symbol" }));
    expect(screen.getByRole("tabpanel").textContent).toContain("symbol 2");
    expect(
      (screen.getByRole("button", { name: "Next symbol" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await user.click(screen.getByRole("tab", { name: "Input" }));
    await user.keyboard("{ArrowRight}");
    expect(
      screen
        .getByRole("tab", { name: "Predictions" })
        .getAttribute("aria-selected"),
    ).toBe("true");
    await user.keyboard("{End}");
    expect(screen.getByRole("tabpanel").textContent).toContain("Explanation");
    await user.keyboard("{Home}");
    expect(screen.getByRole("tabpanel").textContent).toContain("Input");
  });

  it("preserves the symbol and active tab across the modal breakpoint", async () => {
    const { user, dialog } = await openInspector();
    await user.click(screen.getByRole("button", { name: "Next symbol" }));
    await user.click(screen.getByRole("tab", { name: "Explanation" }));
    await user.click(
      screen.getByRole("button", { name: "Draw outside the inspector" }),
    );
    act(() => {
      mobile = true;
      listeners.forEach((listener) => listener());
    });
    await waitFor(() =>
      expect(dialog.contains(document.activeElement)).toBe(true),
    );
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Draw outside the inspector" }),
      ).toBeNull(),
    );
    expect(screen.getByRole("tabpanel").textContent).toContain(
      "Explanation for symbol 2",
    );
    act(() => {
      mobile = false;
      listeners.forEach((listener) => listener());
    });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Draw outside the inspector" }),
      ).toBeTruthy(),
    );
    expect(screen.getByRole("tabpanel").textContent).toContain(
      "Explanation for symbol 2",
    );
  });
});
