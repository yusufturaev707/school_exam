import { AnimatePresence, motion } from 'motion/react';
import { WifiOff } from 'lucide-react';

export function ConnectionBanner({ visible, pendingCount = 0, message }: { visible: boolean; pendingCount?: number; message?: string }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          role="status"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div className="t-sm flex items-start gap-3 bg-streak-soft px-4 py-3 text-streak-ink">
            <WifiOff className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
            <p>
              {message ?? (
                <>
                  Internet vaqtincha uzildi. Xavotir olmang — imtihonni davom ettiravering
                  {pendingCount > 0 ? `, ${pendingCount} ta javobingiz aloqa tiklanganda saqlanadi.` : ', javoblaringiz saqlanadi.'}
                </>
              )}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
