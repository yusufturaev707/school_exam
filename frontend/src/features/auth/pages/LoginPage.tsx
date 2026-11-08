import { Link, useLocation } from 'react-router';
import { IdCard, QrCode } from 'lucide-react';
import type { ReactNode } from 'react';
import { Icon } from '@/components/ui/Icon';

function MethodLink({ to, icon, title, description, state }: { to: string; icon: ReactNode; title: string; description: string; state: unknown }) {
  return (
    <Link to={to} state={state} className="bd-card bd-game bd-tap tap-card is-brand px-3! py-3! text-inherit no-underline hover:shadow-[var(--shadow-md)]">
      <span className="bd-game__art size-14!" aria-hidden="true">
        {icon}
      </span>
      <span className="grow">
        <span className="t-h3 block">{title}</span>
        <span className="t-sm muted block">{description}</span>
      </span>
      <Icon name="chevR" className="text-ink-3" />
    </Link>
  );
}

export default function LoginPage() {
  // Preserve the page the student originally wanted (e.g. a deep link) through the login flow.
  const location = useLocation();
  return (
    <div>
      <h2 className="t-hero">Xush kelibsan! 👋</h2>
      <p className="t-sm muted mt-1">Shaxsiy kabinetingga kirish usulini tanla.</p>

      <div className="mt-5 flex flex-col gap-2">
        <MethodLink
          to="/login/qr"
          state={location.state}
          icon={<QrCode className="size-7" strokeWidth={2.2} />}
          title="QR kod orqali kirish"
          description="Imtihon chiptangdagi QR kodni skanerla"
        />
        <MethodLink
          to="/login/jshshir"
          state={location.state}
          icon={<IdCard className="size-7" strokeWidth={2.2} />}
          title="JSHSHIR orqali kirish"
          description="14 xonali shaxsiy raqamingni kirit"
        />
      </div>

      <div className="bd-card bd-card--cream row mt-6 items-start! gap-2.5! px-3.5! py-3!">
        <Icon name="shield" size={18} className="text-brand" />
        <p className="t-sm muted">Kirishda qiynalsang, oʻqituvching yoki ota-onangdan yordam soʻra. Shaxsiy raqamingni hech kimga aytma.</p>
      </div>
    </div>
  );
}
