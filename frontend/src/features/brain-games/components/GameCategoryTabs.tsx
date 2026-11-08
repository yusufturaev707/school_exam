import { Link } from 'react-router';
import type { GameCategory, GameCategoryInfo } from '../types';
import { CATEGORY_META, CATEGORY_ORDER } from '../utils/meta';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

/** Dizayn: 6 yoʻnalish 3×2 gridda (bd-dirs), yoki kategoriya sahifasida filtr chiplari qatori. */
export function GameCategoryTabs({ categories, active, layout = 'grid' }: { categories: GameCategoryInfo[]; active?: GameCategory; layout?: 'grid' | 'strip' }) {
  const byId = new Map(categories.map((c) => [c.id, c]));
  const ordered = CATEGORY_ORDER.map((id) => byId.get(id)).filter((c) => c !== undefined);

  if (layout === 'strip') {
    return (
      <nav aria-label="Yoʻnalishlar" className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 py-1">
        {ordered.map((c) => {
          const meta = CATEGORY_META[c.id];
          const isActive = c.id === active;
          return (
            <Link key={c.id} to={`/activities/category/${c.id}`} aria-current={isActive ? 'page' : undefined} className={cn('bd-chip bd-chip--filter tap-card shrink-0 no-underline', isActive && 'is-on')}>
              <Icon name={meta.icon} size={16} />
              {meta.short}
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <ul className="bd-dirs lg:grid-cols-6">
      {ordered.map((c) => {
        const meta = CATEGORY_META[c.id];
        return (
          <li key={c.id} className="flex">
            <Link to={`/activities/category/${c.id}`} className={cn('bd-dir bd-tap tap-card w-full no-underline', meta.tone)}>
              <span className="bd-tile">
                <Icon name={meta.icon} size={18} />
              </span>
              <span className="bd-dir__name">{meta.short}</span>
              <span className="bd-dir__meta">{c.activeCount > 0 ? `${c.activeCount} oʻyin` : 'Tez orada'}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
