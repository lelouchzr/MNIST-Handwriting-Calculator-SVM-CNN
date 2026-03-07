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
          <span className="eyebrow">Mode d’emploi</span>
          <button
            className="icon-button"
            onClick={() => dialog.current?.close()}
            aria-label="Fermer l’aide"
            autoFocus
          >
            <X size={23} />
          </button>
        </div>
        <h2 id="help-title">Du trait au résultat.</h2>
        <ol className="help-steps">
          <li>
            <span>01</span>
            <div>
              <h3>Écrivez sur une ligne.</h3>
              <p>
                Espacez les symboles. Une souris, un doigt ou un stylet
                suffisent. Dessinez × avec deux diagonales ; ÷ avec une barre et
                deux points.
              </p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <h3>Vérifiez la lecture.</h3>
              <p>
                Après « Reconnaître », chaque symbole est modifiable. Les scores
                sont des estimations du modèle, pas des garanties. Vous pouvez
                aussi tout saisir au clavier.
              </p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <h3>Suivez le calcul.</h3>
              <p>
                Parenthèses, priorités, nombres négatifs et décimaux sont pris
                en charge. La virgule est acceptée. Appuyez sur Entrée pour
                calculer.
              </p>
            </div>
          </li>
        </ol>
        <div className="help-shortcuts">
          <h3>Raccourcis du brouillon</h3>
          <p>
            <span>Annuler</span>
            <kbd>Ctrl / ⌘ Z</kbd>
          </p>
          <p>
            <span>Rétablir</span>
            <kbd>Ctrl / ⌘ ⇧ Z</kbd>
          </p>
          <p>
            <span>Fermer cette fenêtre</span>
            <kbd>Échap</kbd>
          </p>
        </div>
        <p className="help-privacy">
          Dans la configuration locale, les dessins sont traités sur votre
          ordinateur. Seul l’historique des calculs est conservé dans ce
          navigateur.
        </p>
      </div>
    </dialog>
  );
}
