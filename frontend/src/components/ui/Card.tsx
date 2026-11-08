import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export interface CardProps extends HTMLAttributes<HTMLElement> {
  padded?: boolean;
  as?: 'div' | 'section' | 'article' | 'li';
  /** `cream` — iliq ikkinchi darajali karta, `flat` — soyasiz, chiziqli. */
  tone?: 'default' | 'cream' | 'flat';
}

/** Dizayn: bd-card — radius 18, shadow-sm, ichki boʻshliq 12×16. */
export function Card({ padded = true, as: Tag = 'div', tone = 'default', className, ...rest }: CardProps) {
  return <Tag className={cn('bd-card', tone === 'cream' && 'bd-card--cream', tone === 'flat' && 'bd-card--flat', !padded && 'p-0!', className)} {...rest} />;
}
