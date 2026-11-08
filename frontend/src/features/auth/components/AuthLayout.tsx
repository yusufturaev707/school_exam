import { Outlet } from 'react-router';
import { Logo } from '@/components/shared/Logo';
import { Mascot } from '@/components/shared/Mascot';

/** Kirish sahifalari: hero naqshli brend paneli (telefonda tepada ixcham, kompyuterda chapda) + forma. */
export function AuthLayout() {
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[minmax(420px,1fr)_minmax(480px,1fr)]">
      <aside className="bd-hero rounded-none! px-5! pt-[max(1.25rem,env(safe-area-inset-top))]! pb-14! shadow-none! lg:flex lg:flex-col lg:justify-between lg:p-12!">
        <div className="flex items-center justify-between">
          <Logo light withMascot={false} />
        </div>
        <div className="mt-5 flex items-end gap-4 lg:mt-0 lg:flex-col lg:items-start lg:gap-8">
          <Mascot mood="salom" className="h-24 w-auto md:h-28 lg:h-56" />
          <div>
            <h1 className="t-hero lg:text-[40px] lg:leading-[46px] lg:font-black">Bilim — qiziqarli kashfiyot!</h1>
            <p className="t-body mt-2 hidden max-w-md opacity-85 lg:block">Imtihon topshir, natijangni koʻr va oʻz bilimlaringni yangi choʻqqilarga olib chiq.</p>
          </div>
        </div>
        <p className="t-sm relative hidden opacity-70 lg:block">Maʼlumotlaring xavfsiz saqlanadi.</p>
      </aside>

      <main className="relative -mt-8 rounded-t-[var(--radius-xl)] bg-bg px-4 pt-6 pb-10 md:px-8 lg:mt-0 lg:flex lg:items-center lg:justify-center lg:rounded-none lg:px-12">
        <div className="mx-auto w-full max-w-md">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
