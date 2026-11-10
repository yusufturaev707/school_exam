import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { Button } from '@/components/ui/Button';

interface Props {
  open: boolean;
  total: number;
  answered: number;
  unansweredNumbers: number[];
  onConfirm: () => void;
  onCancel: () => void;
  onJumpToUnanswered: () => void;
}

export function SubmitDialog({ open, total, answered, unansweredNumbers, onConfirm, onCancel, onJumpToUnanswered }: Props) {
  const unanswered = total - answered;
  return (
    <ConfirmationDialog
      open={open}
      title="Imtihonni yakunlaysizmi?"
      description={unanswered === 0 ? 'Barakalla, barcha savollarga javob berdingiz!' : 'Hali vaqtingiz bor. Xohlasangiz, javobsiz savollarga qaytishingiz mumkin.'}
      confirmLabel="Ha, yakunlash"
      cancelLabel="Davom etish"
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      <dl className="grid grid-cols-2 gap-2">
        <div className="rounded-[var(--radius-lg)] bg-brand-soft px-3 py-2.5">
          <dt className="bd-stat__label text-brand-ink!">Javob berilgan</dt>
          <dd className="t-stat tabular text-brand-ink">
            {answered}
            <span className="text-[15px] font-bold"> / {total}</span>
          </dd>
        </div>
        <div className="rounded-[var(--radius-lg)] bg-bg-tint px-3 py-2.5">
          <dt className="bd-stat__label">Javobsiz</dt>
          <dd className="t-stat tabular text-ink">{unanswered}</dd>
        </div>
      </dl>
      {unanswered > 0 && (
        <div className="mt-4">
          <p className="t-sm muted">
            Javobsiz savollar: <span className="tabular font-bold text-ink">{unansweredNumbers.slice(0, 12).join(', ')}{unansweredNumbers.length > 12 ? '…' : ''}</span>
          </p>
          <Button variant="ghost" className="mt-2 -ml-3" onClick={onJumpToUnanswered}>
            Birinchi javobsiz savolga oʻtish
          </Button>
        </div>
      )}
    </ConfirmationDialog>
  );
}
