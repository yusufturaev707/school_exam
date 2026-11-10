import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useLocation } from 'react-router';
import { CircleAlert, LogIn } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { BackLink } from '../components/BackLink';
import { useJshshirLogin } from '../hooks/useSession';
import { authErrorMessage } from '../utils/authErrors';
import { safeRedirect } from '../utils/redirect';
import { cn } from '@/lib/cn';

const schema = z.object({
  jshshir: z
    .string()
    .min(1, 'JSHSHIR raqamingizni kiriting.')
    .regex(/^\d+$/, 'Faqat raqamlar kiritiladi.')
    .length(14, 'JSHSHIR aynan 14 ta raqamdan iborat boʻlishi kerak.'),
});
type FormValues = z.infer<typeof schema>;

export default function JshshirLoginPage() {
  const location = useLocation();
  const login = useJshshirLogin(safeRedirect(location.state));
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { jshshir: '' }, mode: 'onSubmit' });

  const value = watch('jshshir');
  const field = register('jshshir', {
    // Strip anything that isn't a digit as the child types or pastes.
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 14);
    },
  });

  const fieldError = errors.jshshir?.message;
  const serverError = login.isError ? authErrorMessage(login.error) : null;
  const errorText = fieldError ?? serverError;

  return (
    <div>
      <BackLink to="/login" state={location.state} />
      <h2 className="t-hero mt-2">JSHSHIR orqali kirish</h2>
      <p className="t-sm muted mt-1">Shaxsiy raqamingizni guvohnoma yoki metrikangizdan topishingiz mumkin.</p>

      <form
        noValidate
        className="mt-6"
        onSubmit={handleSubmit((v) => {
          if (!login.isPending) login.mutate(v.jshshir);
        })}
      >
        <label htmlFor="jshshir" className="t-h3 mb-2 block">
          JSHSHIR (14 ta raqam)
        </label>
        <div className="relative">
          <input
            id="jshshir"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="go"
            maxLength={14}
            placeholder="00000000000000"
            aria-invalid={!!errorText}
            aria-describedby="jshshir-hint jshshir-error"
            className={cn(
              'tabular h-16 w-full rounded-[var(--radius-md)] border-2 bg-card px-4 pr-20 text-[22px] font-bold tracking-[0.12em] text-ink outline-none transition-colors placeholder:text-line',
              'focus:border-brand focus:ring-4 focus:ring-brand/15',
              errorText ? 'border-danger' : 'border-line',
            )}
            {...field}
          />
          <span id="jshshir-hint" className="tabular absolute top-1/2 right-4 -translate-y-1/2 text-[14px] font-bold text-muted" aria-live="off">
            {value.length}/14
          </span>
        </div>

        <div id="jshshir-error" aria-live="polite" className="min-h-7">
          {errorText && (
            <p className="t-sm mt-2 flex items-start gap-2 text-danger-ink">
              <CircleAlert className="mt-0.5 size-[18px] shrink-0" aria-hidden="true" />
              {errorText}
            </p>
          )}
        </div>

        <Button type="submit" fullWidth loading={login.isPending} className="mt-3" rightIcon={<LogIn className="size-5" aria-hidden="true" />}>
          Kabinetga kirish
        </Button>
      </form>

      {import.meta.env.VITE_USE_MOCKS === 'true' && <p className="t-sm mt-6 rounded-[var(--radius-md)] bg-logic-soft p-3 text-logic-ink">Demo rejim: 12345678901234 raqami bilan kiring.</p>}
    </div>
  );
}
