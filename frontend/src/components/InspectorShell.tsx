import { useEffect, useRef, useSyncExternalStore } from "react";
import type { ReactNode, RefObject } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { CaretLeft, CaretRight, X } from "@phosphor-icons/react";
import type { Token } from "../types";

const mobileQuery = "(max-width: 1099px)";
function subscribe(listener: () => void) {
  const media = window.matchMedia(mobileQuery);
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}

type Props = {
  open: boolean;
  tokens: Pick<Token, "label">[];
  index: number;
  onSelect: (index: number) => void;
  onClose: () => void;
  returnFocus: RefObject<HTMLElement | null>;
  comparison: boolean;
  children: ReactNode;
};

export function InspectorShell({
  open,
  tokens,
  index,
  onSelect,
  onClose,
  returnFocus,
  comparison,
  children,
}: Props) {
  const mobile = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(mobileQuery).matches,
    () => true,
  );
  const popup = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // A desktop user may be drawing when a resize makes inspection modal.
    if (
      open &&
      mobile &&
      popup.current &&
      !popup.current.contains(document.activeElement)
    ) {
      popup.current.focus({ preventScroll: true });
    }
  }, [open, mobile]);
  return (
    <Dialog.Root
      open={open}
      modal={mobile}
      disablePointerDismissal={!mobile}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      onOpenChangeComplete={(next) => {
        // A backdrop press has no focusable destination outside the mobile modal.
        if (!next && mobile && returnFocus.current?.isConnected) {
          returnFocus.current.focus({ preventScroll: true });
        }
      }}
    >
      <Dialog.Portal>
        {mobile && <Dialog.Backdrop className="inspection-backdrop" />}
        <Dialog.Popup
          id="recognition-inspector"
          ref={popup}
          className="inspection-dock"
          initialFocus={popup}
          finalFocus={() =>
            returnFocus.current?.isConnected ? returnFocus.current : false
          }
        >
          <div className="inspection-dock-heading">
            <div>
              <p className="eyebrow">Recognition details</p>
              <Dialog.Title>Inspect</Dialog.Title>
            </div>
            <Dialog.Close className="icon-button" aria-label="Close inspector">
              <X size={23} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="inspection-description">
            {comparison
              ? "Same input. Two models."
              : "From your drawing to the model prediction."}
          </Dialog.Description>
          <div className="inspection-symbol-navigation">
            <label htmlFor="inspected-symbol">Symbol</label>
            <button
              className="icon-button"
              aria-label="Previous symbol"
              disabled={index <= 0}
              onClick={() => onSelect(index - 1)}
            >
              <CaretLeft size={18} />
            </button>
            <select
              id="inspected-symbol"
              value={index}
              disabled={!tokens.length}
              onChange={(event) => onSelect(Number(event.target.value))}
            >
              {tokens.map((token, position) => (
                <option key={position} value={position}>
                  {position + 1} / {tokens.length} · {token.label}
                </option>
              ))}
            </select>
            <button
              className="icon-button"
              aria-label="Next symbol"
              disabled={index >= tokens.length - 1}
              onClick={() => onSelect(index + 1)}
            >
              <CaretRight size={18} />
            </button>
          </div>
          <div className="inspection-body">{children}</div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
