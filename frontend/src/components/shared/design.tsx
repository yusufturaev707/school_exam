import type { ReactNode } from 'react';
import { Link, useNavigate } from 'react-router';
import { Icon, type IconName } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

/*
 * Dizayn tizimidagi kichik qurilish bloklari (bilimdon-dizayn/dizayn-tizimi/components):
 * StatChip, StatTile, SectionHead, TopBar, PageTitle, Avatar, Steps, Sticky.
 */

/** 🔥 seriya / ⭐ ball chipi — emoji emas, ikonka (Androidda bir xil koʻrinadi). */
export function StatChip({ kind, children, label, wiggle = true, className }: { kind: 'streak' | 'star' | 'brand'; children: ReactNode; label?: string; wiggle?: boolean; className?: string }) {
  const icon: IconName = kind === 'streak' ? 'fire' : kind === 'star' ? 'star' : 'trophy';
  return (
    <span className={cn('bd-chip bd-chip--stat', `is-${kind}`, className)} aria-label={label}>
      <span className={wiggle ? 'bd-wiggle' : undefined}>
        <Icon name={icon} size={16} />
      </span>
      <span aria-hidden={label ? true : undefined}>{children}</span>
    </span>
  );
}

/** Dizayn: StatTile (bd-stat) — ikonka + katta raqam + izoh. `tone` — is-<x>. */
export function StatTile({ icon, value, label, tone, center }: { icon: IconName; value: ReactNode; label: string; tone?: string; center?: boolean }) {
  return (
    <div className={cn('bd-stat', tone, center && 'items-center')}>
      <span className="bd-stat__top">
        <Icon name={icon} size={18} />
        <b className="t-stat tabular text-ink">{value}</b>
      </span>
      <span className="bd-stat__label">{label}</span>
    </div>
  );
}

export function StatTiles({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('bd-stats', className)}>{children}</div>;
}

/** Boʻlim sarlavhasi + ixtiyoriy “Barchasi ›” havolasi. */
export function SectionHead({ title, id, link, desktopLarge }: { title: string; id?: string; link?: { to: string; label: string }; desktopLarge?: boolean }) {
  return (
    <div className="sec-head">
      <h2 id={id} className={cn('t-h2', desktopLarge && 'lg:text-[20px]')}>
        {title}
      </h2>
      {link && (
        <Link to={link.to} className="link">
          {link.label}
          <Icon name="chevR" size={16} />
        </Link>
      )}
    </div>
  );
}

export function Section({ title, link, children, className, id }: { title?: string; link?: { to: string; label: string }; children: ReactNode; className?: string; id?: string }) {
  return (
    <section className={cn('sec', className)} aria-labelledby={id}>
      {title && <SectionHead title={title} id={id} link={link} desktopLarge />}
      {children}
    </section>
  );
}

/** Ichki sahifalar tepasi: ← orqaga + sarlavha (dizayn: bd-topbar). */
/**
 * `preferHistory` — return to wherever the student came from (browser history inside the app);
 * `back` is used only when there is no such history (deep link, new tab).
 */
export function TopBar({ title, back, onBack, right, closeIcon, preferHistory }: { title?: ReactNode; back?: string; onBack?: () => void; right?: ReactNode; closeIcon?: boolean; preferHistory?: boolean }) {
  const navigate = useNavigate();
  const go = () => {
    if (onBack) return onBack();
    const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0; // React Router's position in this tab's history
    if ((preferHistory || !back) && idx > 0) return navigate(-1);
    navigate(back ?? '/');
  };
  return (
    <div className="bd-topbar -mx-3 lg:mx-0 lg:px-0">
      <button type="button" className="bd-iconbtn hover:bg-bg-tint" aria-label={closeIcon ? 'Yopish' : 'Orqaga'} onClick={go}>
        <Icon name={closeIcon ? 'x' : 'arrowL'} />
      </button>
      {title && <span className="bd-topbar__title grow truncate">{title}</span>}
      {right}
    </div>
  );
}

/** Asosiy boʻlim sahifalari sarlavhasi (Imtihonlar, Natijalarim…): t-hero, kompyuterda display. */
export function PageTitle({ title, subtitle, right }: { title: ReactNode; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mt-2 mb-1 flex items-start justify-between gap-3 lg:mt-0 lg:mb-2">
      <div className="min-w-0">
        <h1 className="t-hero lg:text-[32px] lg:leading-[38px] lg:font-black lg:tracking-[-0.02em]">{title}</h1>
        {subtitle && <p className="t-sm muted mt-0.5 lg:text-[15px] lg:leading-[22px] lg:font-medium">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

/** “6-B” → “6-B sinf”; backend allaqachon “sinf” deb yuborsa, takrorlamaydi. */
export const classLabel = (className?: string | null) => (className ? (/sinf/i.test(className) ? className : `${className} sinf`) : '');

export function initials(first?: string, last?: string) {
  return `${first?.[0] ?? ''}${last?.[0] ?? ''}`.toUpperCase() || '?';
}

export function Avatar({ first, last, photoUrl, size, className }: { first?: string; last?: string; photoUrl?: string | null; size?: number; className?: string }) {
  const style = size ? { width: size, height: size, fontSize: Math.round(size / 3) } : undefined;
  return (
    <span className={cn('bd-avatar overflow-hidden', className)} style={style} aria-hidden="true">
      {photoUrl ? <img src={photoUrl} alt="" className="size-full object-cover" /> : initials(first, last)}
    </span>
  );
}

/** “Qanday ishlaydi?” raqamli qadamlar. */
export function Steps({ items, tone = 'is-brand', compact }: { items: Array<{ title?: string; text: ReactNode }>; tone?: string; compact?: boolean }) {
  return (
    <ol className={cn('flex flex-col', compact ? 'gap-2' : 'gap-3')}>
      {items.map((s, i) => (
        <li key={i} className={cn('flex gap-3', compact ? 'items-center gap-2.5' : 'items-start')}>
          <span
            className={cn('bd-tile rounded-full! text-[12px] font-black text-[var(--ci)]!', tone, compact ? 'size-[22px]!' : 'size-6!')}
            aria-hidden="true"
          >
            {i + 1}
          </span>
          {s.title ? (
            <div>
              <div className="t-h3">{s.title}</div>
              <p className="t-sm muted">{s.text}</p>
            </div>
          ) : (
            <span className="t-sm">{s.text}</span>
          )}
        </li>
      ))}
    </ol>
  );
}

/** Pastda yopishgan asosiy amal (bosh barmoq zonasi). Sahifa kontentiga pastdan ≥ 120px boʻshliq kerak. */
export function Sticky({ children, note, className }: { children: ReactNode; note?: ReactNode; className?: string }) {
  return (
    <div className={cn('bd-sticky', className)}>
      <div className="bd-sticky__in flex flex-col gap-2">
        {children}
        {note && <p className="t-xs faint -mt-1 text-center">{note}</p>}
      </div>
    </div>
  );
}
