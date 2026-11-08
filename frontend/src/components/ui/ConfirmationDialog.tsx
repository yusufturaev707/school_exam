import type { ReactNode } from 'react';
import { Button } from './Button';
import { Modal } from './Modal';

export interface ConfirmationDialogProps {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationDialog({ open, title, description, children, confirmLabel, cancelLabel, loading, onConfirm, onCancel }: ConfirmationDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      dismissible={!loading}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="secondary" size="lg" onClick={onCancel} disabled={loading} className="sm:min-w-36" aria-label={cancelLabel}>
            {cancelLabel}
          </Button>
          <Button size="lg" onClick={onConfirm} loading={loading} className="sm:min-w-36" aria-label={confirmLabel}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {children}
    </Modal>
  );
}
