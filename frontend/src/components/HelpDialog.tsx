import { useEffect, useRef } from "react";
import { X } from "@phosphor-icons/react";

export function HelpDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return (
    <dialog
      ref={dialog}
      className="help-dialog"
      aria-labelledby="help-title"
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialog.current) dialog.current?.close();
      }}
    >
      <div className="help-content">
        <div className="help-heading">
          <span className="eyebrow">How to use</span>
          <button
            className="icon-button"
            onClick={() => dialog.current?.close()}
            aria-label="Close help"
            autoFocus
          >
            <X size={23} />
          </button>
        </div>
        <h2 id="help-title">From ink to answer.</h2>
        <ol className="help-steps">
          <li>
            <span>01</span>
            <div>
              <h3>Write on one line.</h3>
              <p>
                Leave a gap between symbols. Use a mouse, finger or stylus. Draw
                × with two diagonals and ÷ with a bar and two dots.
              </p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <h3>Check the recognition.</h3>
              <p>
                Choose SVM, CNN or Compare before recognition. Compare shows
                both models on the same input; choose which expression to use
                for the calculation. SVM probabilities are calibrated; CNN
                softmax scores are not. After choosing Recognize, you can edit
                each symbol. Scores are model estimates, not guarantees. You can
                also type the entire expression. Use Inspect or select a
                numbered box to see the input pixels, all class scores and a
                masking sensitivity map. Turn off Segments to draw over a
                detected box.
              </p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <h3>Follow the calculation.</h3>
              <p>
                Parentheses, operator precedence, negative numbers and decimals
                are supported. Decimal commas also work. Press Enter to
                calculate.
              </p>
            </div>
          </li>
        </ol>
        <div className="help-shortcuts">
          <h3>Drawing shortcuts</h3>
          <p>
            <span>Undo</span>
            <kbd>Ctrl / ⌘ Z</kbd>
          </p>
          <p>
            <span>Redo</span>
            <kbd>Ctrl / ⌘ ⇧ Z</kbd>
          </p>
          <p>
            <span>Close this window</span>
            <kbd>Esc</kbd>
          </p>
        </div>
        <p className="help-privacy">
          In the local setup, drawings are processed on your computer. Only your
          calculation history is saved in this browser.
        </p>
      </div>
    </dialog>
  );
}
