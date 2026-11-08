import { NavLink, Outlet } from 'react-router';
import { Icon, type IconName } from '@/components/ui/Icon';
import { Mascot } from '@/components/shared/Mascot';
import { cn } from '@/lib/cn';

/* Dizayn: BottomNav (telefon) va ScreenHomeDesktop yon paneli (≥1024px, 248px). */
const NAV: Array<{ to: string; label: string; icon: IconName; end?: boolean }> = [
  { to: '/', label: 'Bosh sahifa', icon: 'home', end: true },
  { to: '/exam', label: 'Imtihon', icon: 'exam' },
  { to: '/activities', label: 'Oʻyinlar', icon: 'game' },
  { to: '/results', label: 'Natijalar', icon: 'chart' },
  { to: '/profile', label: 'Profil', icon: 'user' },
];

function BottomNavigation() {
  return (
    <nav aria-label="Asosiy menyu" className="bd-nav lg:hidden">
      {NAV.map(({ to, label, icon, end }) => (
        <NavLink key={to} to={to} end={end} className={({ isActive }) => cn('tap-card', isActive && 'is-on')}>
          <span className="bd-nav__pill">
            <Icon name={icon} size={22} />
          </span>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function Sidebar() {
  return (
    <aside className="bd-side hidden lg:flex">
      <NavLink to="/" className="bd-side__brand" aria-label="Bilimdon — bosh sahifa">
        <Mascot mood="salom" size={40} />
        Bilimdon
      </NavLink>
      <nav aria-label="Asosiy menyu" className="flex flex-col gap-1">
        {NAV.map(({ to, label, icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => cn('bd-side__item', isActive && 'is-on')}>
            <Icon name={icon} size={22} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="bd-card bd-card--cream mt-auto p-3.5!">
        <div className="row">
          <Mascot mood="oylayapti" size={44} />
          <p className="t-sm">Har kuni 10 daqiqa — miyang uchun eng yaxshi mashq!</p>
        </div>
      </div>
    </aside>
  );
}

/** Shell for the authenticated area (not used during the exam itself, which is distraction-free). */
export function AppLayout() {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <main className="mx-auto w-full max-w-[1160px] px-4 pt-[env(safe-area-inset-top)] pb-28 md:px-6 lg:px-10 lg:pt-7 lg:pb-12">
          <Outlet />
        </main>
      </div>
      <BottomNavigation />
    </div>
  );
}

/** Minimal shell for focus screens (exam intro, agreement, completion, game result): sahifaning oʻzi TopBar chizadi. */
export function FocusLayout() {
  return (
    <div className="min-h-dvh">
      <main className="mx-auto w-full max-w-[640px] px-4 pt-[env(safe-area-inset-top)] pb-36 md:pt-4">
        <Outlet />
      </main>
    </div>
  );
}
