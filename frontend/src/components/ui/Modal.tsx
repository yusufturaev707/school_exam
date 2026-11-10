import { useEffect, useId, useRef, type ReactNode, type TouchEvent } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/cn';
import { Icon } from './Icon';
import { IconButton } from './IconButton';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  /** `sheet` slides up from the bottom on phones and becomes a centred dialog on tablet+. */
  variant?: 'sheet' | 'dialog';
  dismissible?: boolean;
  className?: string;
}

/**
 * Accessible modal built on the native <dialog> element:
 * focus trapping, Esc handling and inert background come from the platform.
 */
export function Modal({ open, onClose, title, description, children, footer, variant = 'sheet', dismissible = true, className }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ y: number; dy: number } | null>(null);
  const titleId = useId();
  const descId = useId();
  const draggable = variant === 'sheet' && dismissible;

  // Phones: drag the sheet's top (handle + title) down to dismiss it.
  const dragHandlers = draggable
    ? {
        onTouchStart: (e: TouchEvent<HTMLDivElement>) => {
          if (window.matchMedia('(min-width: 768px)').matches) return;
          drag.current = { y: e.touches[0]!.clientY, dy: 0 };
          if (panelRef.current) panelRef.current.style.transition = 'none';
        },
        onTouchMove: (e: TouchEvent<HTMLDivElement>) => {
          if (!drag.current || !panelRef.current) return;
          drag.current.dy = Math.max(0, e.touches[0]!.clientY - drag.current.y);
          panelRef.current.style.transform = `translateY(${drag.current.dy}px)`;
        },
        onTouchEnd: () => {
          const d = drag.current;
          drag.current = null;
          const panel = panelRef.current;
          if (!d || !panel) return;
          panel.style.transition = 'transform 180ms ease-out';
          if (d.dy > 90) onClose();
          else panel.style.transform = '';
        },
      }
    : {};

  useEffect(() => {
    if (!open && panelRef.current) panelRef.current.style.transform = '';
  }, [open]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // The dialog is portalled to <body>; while it is open the app behind it is `inert`
  // (out of the accessibility tree, not focusable, not clickable). showModal() traps focus inside.
  useEffect(() => {
    if (!open) return;
    const root = document.getElementById('root');
    if (!root) return;
    const opener = document.activeElement as HTMLElement | null;
    root.inert = true;
    root.setAttribute('aria-hidden', 'true');
    return () => {
      // Another modal may still be open (e.g. a confirmation over a sheet): only release the app when none is.
      const othersOpen = [...document.querySelectorAll('dialog[open]')].some((d) => d !== ref.current);
      if (!othersOpen) {
        root.inert = false;
        root.removeAttribute('aria-hidden');
      }
      opener?.focus?.();
    };
  }, [open]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const onCancel = (e: Event) => {
      e.preventDefault();
      if (dismissible) onClose();
    };
    dialog.addEventListener('cancel', onCancel);
    return () => dialog.removeEventListener('cancel', onCancel);
  }, [dismissible, onClose]);

  return createPortal(
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onClick={(e) => {
        if (dismissible && e.target === ref.current) onClose();
      }}
      className={cn(
        'm-0 max-h-[92dvh] w-full overflow-visible bg-transparent p-0 text-ink backdrop:bg-[#11302a]/45 backdrop:backdrop-blur-[2px]',
        variant === 'sheet' ? 'mt-auto max-w-none md:m-auto md:max-w-lg' : 'm-auto max-w-[calc(100%-32px)] md:max-w-md',
      )}
    >
      {open && (
        <div
          ref={panelRef}
          className={cn(
            'flex max-h-[92dvh] flex-col bg-card shadow-[var(--shadow-md)] motion-safe:animate-[sheet-in_220ms_ease-out]',
            variant === 'sheet' ? 'rounded-t-[var(--radius-xl)] md:rounded-[var(--radius-xl)]' : 'rounded-[var(--radius-xl)]',
            className,
          )}
        >
          <div {...dragHandlers} className={cn(draggable && 'touch-none md:touch-auto')}>
          {variant === 'sheet' && <div aria-hidden="true" className="mx-auto mt-3 h-1.5 w-12 rounded-full bg-line md:hidden" />}
          <div className="flex items-start gap-3 px-5 pt-4 md:px-6 md:pt-6">
            <div className="min-w-0 flex-1">
              <h2 id={titleId} className="t-h2">
                {title}
              </h2>
              {description && (
                <p id={descId} className="t-sm muted mt-1">
                  {description}
                </p>
              )}
            </div>
            {dismissible && <IconButton label="Yopish" variant="ghost" icon={<Icon name="x" />} onClick={onClose} className="-mt-1 -mr-2" />}
          </div>
          </div>
          {children && <div className="min-h-0 overflow-y-auto px-5 py-4 md:px-6">{children}</div>}
          {footer && <div className="safe-bottom flex flex-col-reverse gap-3 px-5 pt-2 pb-5 sm:flex-row sm:justify-end md:px-6 md:pb-6">{footer}</div>}
        </div>
      )}
      <style>{'@keyframes sheet-in{from{transform:translateY(24px);opacity:0}to{transform:none;opacity:1}}'}</style>
    </dialog>,
    document.body,
  );
}
