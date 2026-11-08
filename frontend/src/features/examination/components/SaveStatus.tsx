import { CloudCheck, CloudOff, LoaderCircle } from 'lucide-react';
import type { SyncState } from '../services/answerSyncEngine';

/** Small, calm autosave indicator — reassures the child their answers are safe. */
export function SaveStatus({ sync, online }: { sync: SyncState; online: boolean }) {
  let icon = <CloudCheck className="size-4 text-success" aria-hidden="true" />;
  let text = 'Saqlandi';
  if (!online || sync.phase === 'retrying') {
    icon = <CloudOff className="size-4 text-streak" aria-hidden="true" />;
    text = 'Aloqa kutilmoqda';
  } else if (sync.phase === 'saving' || sync.pendingCount > 0) {
    icon = <LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden="true" />;
    text = 'Saqlanmoqda';
  }
  return (
    <span className="t-xs muted inline-flex items-center gap-1.5" role="status" aria-live="polite">
      {icon}
      {text}
    </span>
  );
}
