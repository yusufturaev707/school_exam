import { Link } from 'react-router';
import { Icon } from '@/components/ui/Icon';

export function BackLink({ to, label = 'Orqaga', state }: { to: string; label?: string; state?: unknown }) {
  return (
    <Link to={to} state={state} className="bd-btn bd-btn--ghost -ml-2 h-11! text-[15px]!">
      <Icon name="arrowL" />
      {label}
    </Link>
  );
}
