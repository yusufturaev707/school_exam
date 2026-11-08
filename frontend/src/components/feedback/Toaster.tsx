import { AnimatePresence, motion } from 'motion/react';
import { useToastStore, type ToastTone } from './toastStore';
import { Icon, type IconName } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

const icons: Record<ToastTone, IconName> = { info: 'info', success: 'check', warning: 'alert' };
const tones: Record<ToastTone, string> = {
  info: 'is-brand',
  success: 'bg-success-soft! text-success-ink!',
  warning: 'is-logic',
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  return (
    <div aria-live="polite" role="status" className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex flex-col items-center gap-2 px-4">
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <motion.button
            key={t.id}
            type="button"
            layout
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
            onClick={() => dismiss(t.id)}
            className="bd-card pointer-events-auto flex w-full max-w-md items-center gap-3 text-left text-[15px] font-bold shadow-[var(--shadow-md)]!"
          >
            <span className={cn('bd-tile', tones[t.tone])}>
              <Icon name={icons[t.tone]} size={18} />
            </span>
            <span>{t.message}</span>
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}
