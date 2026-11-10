import { memo } from 'react';
import type { Shape, ShapeColor, ShapeType } from '../../types';
import { cn } from '@/lib/cn';

export const SHAPE_COLORS: Record<ShapeColor, string> = {
  teal: '#17776A',
  yellow: '#F2B84B',
  pink: '#E0679F',
  blue: '#3B7DD8',
  orange: '#EC7A36',
  purple: '#8A5FDE',
};
const SHAPE_NAMES: Record<ShapeType, string> = { circle: 'doira', square: 'kvadrat', triangle: 'uchburchak', star: 'yulduz', diamond: 'romb', hexagon: 'oltiburchak', arrow: 'strelka' };
const COLOR_NAMES: Record<ShapeColor, string> = { teal: 'yashil', yellow: 'sariq', pink: 'pushti', blue: 'koʻk', orange: 'toʻq sariq', purple: 'binafsha' };
const DIRECTIONS: Record<number, string> = { 0: 'oʻngga qaragan', 90: 'pastga qaragan', 180: 'chapga qaragan', 270: 'yuqoriga qaragan' };

/** Spoken description, e.g. "2 ta sariq yulduz" — shapes are never conveyed by colour alone. */
export function describeShape(s: Shape): string {
  const base = `${s.count > 1 ? `${s.count} ta ` : ''}${COLOR_NAMES[s.color]} ${SHAPE_NAMES[s.type]}`;
  return s.type === 'arrow' ? `${base}, ${DIRECTIONS[((s.rotation % 360) + 360) % 360] ?? ''}` : base;
}

const poly = (pts: Array<[number, number]>) => pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
const ring = (n: number, r: number, offset = -Math.PI / 2) => Array.from({ length: n }, (_, i): [number, number] => [Math.cos(offset + (i * 2 * Math.PI) / n) * r, Math.sin(offset + (i * 2 * Math.PI) / n) * r]);

function Figure({ type, r, fill }: { type: ShapeType; r: number; fill: string }) {
  const stroke = { stroke: '#183B36', strokeOpacity: 0.18, strokeWidth: 2, strokeLinejoin: 'round' as const };
  switch (type) {
    case 'circle':
      return <circle r={r} fill={fill} {...stroke} />;
    case 'square':
      return <rect x={-r * 0.86} y={-r * 0.86} width={r * 1.72} height={r * 1.72} rx={r * 0.22} fill={fill} {...stroke} />;
    case 'triangle':
      return <polygon points={poly([[0, -r], [r * 0.98, r * 0.72], [-r * 0.98, r * 0.72]])} fill={fill} {...stroke} />;
    case 'diamond':
      return <polygon points={poly([[0, -r], [r * 0.78, 0], [0, r], [-r * 0.78, 0]])} fill={fill} {...stroke} />;
    case 'hexagon':
      return <polygon points={poly(ring(6, r, 0))} fill={fill} {...stroke} />;
    case 'star': {
      const outer = ring(5, r);
      const inner = ring(5, r * 0.45, -Math.PI / 2 + Math.PI / 5);
      return <polygon points={poly(outer.flatMap((p, i) => [p, inner[i]!]))} fill={fill} {...stroke} />;
    }
    case 'arrow':
      return <polygon points={poly([[-r, -r * 0.24], [r * 0.15, -r * 0.24], [r * 0.15, -r * 0.7], [r, 0], [r * 0.15, r * 0.7], [r * 0.15, r * 0.24], [-r, r * 0.24]])} fill={fill} {...stroke} />;
  }
}

const LAYOUT: Record<number, Array<[number, number]>> = {
  1: [[50, 50]],
  2: [[29, 50], [71, 50]],
  3: [[29, 33], [71, 33], [50, 71]],
  4: [[29, 29], [71, 29], [29, 71], [71, 71]],
};
const RADIUS: Record<number, number> = { 1: 34, 2: 19, 3: 17, 4: 16 };

export const ShapeGlyph = memo(function ShapeGlyph({ shape, className, labelled = true }: { shape: Shape; className?: string; labelled?: boolean }) {
  const r = RADIUS[shape.count] ?? 16;
  return (
    <svg viewBox="0 0 100 100" className={cn('block', className)} role={labelled ? 'img' : undefined} aria-label={labelled ? describeShape(shape) : undefined} aria-hidden={labelled ? undefined : true}>
      {(LAYOUT[shape.count] ?? LAYOUT[1]!).map(([cx, cy], i) => (
        <g key={i} transform={`translate(${cx} ${cy}) rotate(${shape.rotation})`}>
          <Figure type={shape.type} r={r} fill={SHAPE_COLORS[shape.color]} />
        </g>
      ))}
    </svg>
  );
});
