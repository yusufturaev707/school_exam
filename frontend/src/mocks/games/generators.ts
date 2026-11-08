/**
 * DEV-ONLY content generators — stand-ins for what the backend produces per session.
 * Every generated question carries its correct option and an explanation, which stay on the
 * "server" side; the client only ever receives the public projection (see gameServer.ts).
 */
import type { GameDifficulty, Shape, ShapeColor, ShapeType } from '@/features/brain-games/types';

export type Rng = () => number;
export const int = (rng: Rng, min: number, max: number) => min + Math.floor(rng() * (max - min + 1));
export const pick = <T>(rng: Rng, items: readonly T[]): T => items[Math.floor(rng() * items.length)]!;
export function shuffle<T>(rng: Rng, items: readonly T[]): T[] {
  const a = [...items];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j]!, a[i]!];
  }
  return a;
}

/* ================================================================ memory */

export const MEMORY_FACES = ['apple', 'cat', 'fish', 'rocket', 'sun', 'moon', 'bird', 'flower', 'star', 'tree'] as const;
export const MEMORY_PAIRS: Record<GameDifficulty, number> = { easy: 4, medium: 6, hard: 8 };

export interface MemoryInternal {
  kind: 'memory';
  pairs: number;
  cards: Array<{ id: string; face: string }>;
}

export function generateMemory(rng: Rng, difficulty: GameDifficulty): MemoryInternal {
  const pairs = MEMORY_PAIRS[difficulty];
  const faces = shuffle(rng, MEMORY_FACES).slice(0, pairs);
  const cards = shuffle(rng, [...faces, ...faces]).map((face, i) => ({ id: `c${i + 1}`, face }));
  return { kind: 'memory', pairs, cards };
}

/**
 * Server-side replay of the move log the client sends on completion.
 * The score is derived from this replay — a client cannot just claim "all pairs found".
 */
export function replayMemory(cards: MemoryInternal['cards'], moves: unknown): { valid: boolean; moves: number; matchedPairs: number } {
  const invalid = { valid: false, moves: 0, matchedPairs: 0 };
  if (!Array.isArray(moves) || moves.length > 500) return invalid;
  const face = new Map(cards.map((c) => [c.id, c.face]));
  const matched = new Set<string>();
  for (const move of moves) {
    if (!Array.isArray(move) || move.length !== 2) return invalid;
    const [a, b] = move as unknown[];
    if (typeof a !== 'string' || typeof b !== 'string' || a === b || !face.has(a) || !face.has(b)) return invalid;
    if (matched.has(a) || matched.has(b)) return invalid;
    if (face.get(a) === face.get(b)) {
      matched.add(a);
      matched.add(b);
    }
  }
  const matchedPairs = matched.size / 2;
  return { valid: matchedPairs === cards.length / 2, moves: moves.length, matchedPairs };
}

/* ================================================================ shared quiz shape */

export interface QuizQuestionInternal<TOption> {
  id: string;
  options: Array<{ id: string } & TOption>;
  correctOptionId: string;
  explanation: string;
}

function withOptions<TOption>(rng: Rng, qid: string, answer: TOption, distractors: TOption[]) {
  const all = shuffle(rng, [answer, ...distractors.slice(0, 3)]);
  const options = all.map((o, i) => ({ id: `${qid}_o${i + 1}`, ...o }));
  return { options, correctOptionId: options[all.indexOf(answer)]!.id };
}

/* ================================================================ missing number */

export interface MissingNumberQuestionInternal extends QuizQuestionInternal<{ value: number }> {
  sequence: Array<number | null>;
}
export interface MissingNumberInternal {
  kind: 'missing-number';
  questions: MissingNumberQuestionInternal[];
}

interface Sequence {
  terms: number[];
  /** Allowed positions of the hidden term (never the first, so the rule is always visible). */
  hideable: number[];
  rule: string;
  /** Concrete calculation that produces the hidden term at index i. */
  calc: (i: number) => string;
}

const LEN = 5;
const seq = (first: number, next: (prev: number, k: number, all: number[]) => number) => {
  const t = [first];
  for (let k = 1; k < LEN; k++) t.push(next(t[k - 1]!, k, t));
  return t;
};

type Template = (rng: Rng) => Sequence;

const add: (min: number, max: number, dMin: number, dMax: number) => Template = (min, max, dMin, dMax) => (rng) => {
  const d = int(rng, dMin, dMax);
  const t = seq(int(rng, min, max), (p) => p + d);
  return { terms: t, hideable: [1, 2, 3, 4], rule: `Har bir son oldingisidan ${d} taga katta.`, calc: (i) => `${t[i - 1]} + ${d} = ${t[i]}` };
};
const sub: Template = (rng) => {
  const d = int(rng, 2, 9);
  const t = seq(int(rng, 50, 90), (p) => p - d);
  return { terms: t, hideable: [1, 2, 3, 4], rule: `Har bir son oldingisidan ${d} taga kichik.`, calc: (i) => `${t[i - 1]} − ${d} = ${t[i]}` };
};
const mul: (maxStart: number, ratios: number[]) => Template = (maxStart, ratios) => (rng) => {
  const r = pick(rng, ratios);
  const t = seq(int(rng, 1, maxStart), (p) => p * r);
  return { terms: t, hideable: [1, 2, 3, 4], rule: `Har bir son oldingisidan ${r} marta katta.`, calc: (i) => `${t[i - 1]} × ${r} = ${t[i]}` };
};
const growing: Template = (rng) => {
  const d0 = int(rng, 1, 3);
  const t = seq(int(rng, 1, 10), (p, k) => p + d0 + k - 1);
  return {
    terms: t,
    hideable: [2, 3, 4],
    rule: `Qo‘shiladigan son har safar 1 taga oshadi: +${d0}, +${d0 + 1}, +${d0 + 2}…`,
    calc: (i) => `${t[i - 1]} + ${d0 + i - 1} = ${t[i]}`,
  };
};
const squares: Template = (rng) => {
  const n0 = int(rng, 1, 5);
  const t = seq(n0 * n0, (_p, k) => (n0 + k) * (n0 + k));
  return { terms: t, hideable: [1, 2, 3, 4], rule: 'Bular ketma-ket sonlarning kvadratlari (sonni o‘ziga ko‘paytiramiz).', calc: (i) => `${n0 + i} × ${n0 + i} = ${t[i]}` };
};
const fibonacci: Template = (rng) => {
  const a = int(rng, 1, 3);
  const t = seq(a, (p, k, all) => (k === 1 ? int(rng, a, a + 3) : p + all[k - 2]!));
  return { terms: t, hideable: [2, 3, 4], rule: 'Har bir son oldingi ikkita son yig‘indisiga teng.', calc: (i) => `${t[i - 2]} + ${t[i - 1]} = ${t[i]}` };
};
const doublePlusOne: Template = (rng) => {
  const t = seq(int(rng, 1, 4), (p) => p * 2 + 1);
  return { terms: t, hideable: [1, 2, 3, 4], rule: 'Har bir sonni 2 ga ko‘paytirib, 1 qo‘shamiz.', calc: (i) => `${t[i - 1]} × 2 + 1 = ${t[i]}` };
};

const NUMBER_TEMPLATES: Record<GameDifficulty, Template[]> = {
  easy: [add(1, 20, 2, 9), add(1, 30, 2, 5), sub],
  medium: [mul(4, [2, 3]), add(10, 40, 11, 25), growing],
  hard: [squares, fibonacci, doublePlusOne, mul(5, [3, 4])],
};

export function generateMissingNumber(rng: Rng, difficulty: GameDifficulty, count = 8): MissingNumberInternal {
  const templates = NUMBER_TEMPLATES[difficulty];
  const questions: MissingNumberQuestionInternal[] = [];
  const seen = new Set<string>();
  while (questions.length < count) {
    const s = pick(rng, templates)(rng);
    const hide = pick(rng, s.hideable);
    const key = `${s.terms.join(',')}@${hide}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const answer = s.terms[hide]!;
    const step = Math.max(1, Math.abs(answer - s.terms[hide - 1]!));
    const near = [answer + 1, answer - 1, answer + 2, answer - 2, answer + step, answer - step, answer + 10];
    const distractors = shuffle(rng, [...new Set(near)].filter((v) => v >= 0 && v !== answer)).slice(0, 3);
    const qid = `mn${questions.length + 1}`;
    const { options, correctOptionId } = withOptions(
      rng,
      qid,
      { value: answer },
      distractors.map((value) => ({ value })),
    );
    questions.push({
      id: qid,
      sequence: s.terms.map((v, i) => (i === hide ? null : v)),
      options,
      correctOptionId,
      explanation: `${s.rule} ${s.calc(hide)}.`,
    });
  }
  return { kind: 'missing-number', questions };
}

/* ================================================================ pattern master */

export interface PatternQuestionInternal extends QuizQuestionInternal<{ shape: Shape }> {
  sequence: Array<Shape | null>;
}
export interface PatternInternal {
  kind: 'pattern';
  questions: PatternQuestionInternal[];
}

const PLAIN_SHAPES: ShapeType[] = ['circle', 'square', 'triangle', 'star', 'diamond', 'hexagon'];
const COLORS: ShapeColor[] = ['teal', 'yellow', 'pink', 'blue', 'orange', 'purple'];
export const SHAPE_NAMES: Record<ShapeType, string> = { circle: 'doira', square: 'kvadrat', triangle: 'uchburchak', star: 'yulduz', diamond: 'romb', hexagon: 'oltiburchak', arrow: 'strelka' };
export const COLOR_NAMES: Record<ShapeColor, string> = { teal: 'yashil', yellow: 'sariq', pink: 'pushti', blue: 'ko‘k', orange: 'to‘q sariq', purple: 'binafsha' };
export const DIRECTION_NAMES: Record<number, string> = { 0: 'o‘ngga', 90: 'pastga', 180: 'chapga', 270: 'yuqoriga' };

/** Repeating motifs; letters index into the chosen values. */
const MOTIFS = { AB: [0, 1], ABC: [0, 1, 2], AAB: [0, 0, 1], ABB: [0, 1, 1] } as const;
type Motif = keyof typeof MOTIFS;

const SHOWN = 6; // visible items; item 7 is the answer — every rule repeats at least twice

interface AttrRule<T> {
  at: (i: number) => T;
  explain: string;
  /** Plausible wrong values (seen in the sequence or a natural alternative). */
  alternatives: T[];
}

function cycle<T>(rng: Rng, pool: readonly T[], motif: Motif, name: (v: T) => string, label: string): AttrRule<T> {
  const size = Math.max(...MOTIFS[motif]) + 1;
  const values = shuffle(rng, pool).slice(0, size);
  const order = MOTIFS[motif].map((k) => values[k]!);
  return {
    at: (i) => order[i % order.length]!,
    explain: `${label}: ${order.map(name).join(' → ')}, keyin yana boshidan.`,
    alternatives: [...values, ...shuffle(rng, pool.filter((v) => !values.includes(v))).slice(0, 1)],
  };
}
const fixed = <T>(value: T, alternatives: T[]): AttrRule<T> => ({ at: () => value, explain: '', alternatives });

function rotationRule(rng: Rng): AttrRule<number> {
  const start = pick(rng, [0, 90, 180, 270]);
  return { at: (i) => (start + i * 90) % 360, explain: 'Strelka har safar soat mili bo‘yicha chorak aylanadi.', alternatives: [0, 90, 180, 270] };
}

interface PatternPlan {
  type: AttrRule<ShapeType>;
  color: AttrRule<ShapeColor>;
  rotation: AttrRule<number>;
  count: AttrRule<number>;
}

function plan(rng: Rng, difficulty: GameDifficulty): PatternPlan {
  const shapeCycle = (m: Motif) => cycle(rng, PLAIN_SHAPES, m, (v) => SHAPE_NAMES[v], 'Shakllar tartibi');
  const colorCycle = (m: Motif) => cycle(rng, COLORS, m, (v) => COLOR_NAMES[v], 'Ranglar tartibi');
  const countCycle = (m: Motif) => cycle(rng, [1, 2, 3], m, String, 'Shakllar soni');
  const oneShape = () => fixed(pick(rng, PLAIN_SHAPES), PLAIN_SHAPES);
  const oneColor = () => fixed(pick(rng, COLORS), COLORS);
  const noRotation = fixed(0, [0]);
  const one = fixed(1, [1, 2]);
  const arrow = fixed<ShapeType>('arrow', ['arrow']);

  const motifs: Motif[] = ['AB', 'ABC', 'AAB', 'ABB'];
  if (difficulty === 'easy') {
    return rng() < 0.5
      ? { type: shapeCycle(pick(rng, motifs)), color: oneColor(), rotation: noRotation, count: one }
      : { type: oneShape(), color: colorCycle(pick(rng, motifs)), rotation: noRotation, count: one };
  }
  if (difficulty === 'medium') {
    const variant = int(rng, 0, 2);
    if (variant === 0) return { type: shapeCycle('AB'), color: colorCycle('ABC'), rotation: noRotation, count: one };
    if (variant === 1) return { type: arrow, color: colorCycle('AB'), rotation: rotationRule(rng), count: one };
    return { type: shapeCycle('ABC'), color: oneColor(), rotation: noRotation, count: countCycle('AB') };
  }
  const variant = int(rng, 0, 2);
  if (variant === 0) return { type: shapeCycle('ABC'), color: colorCycle('AB'), rotation: noRotation, count: countCycle('ABC') };
  if (variant === 1) return { type: arrow, color: colorCycle('ABC'), rotation: rotationRule(rng), count: countCycle('AB') };
  return { type: shapeCycle('AAB'), color: colorCycle('ABC'), rotation: noRotation, count: countCycle('AB') };
}

const shapeKey = (s: Shape) => `${s.type}|${s.color}|${s.rotation}|${s.count}`;

export function describeShape(s: Shape): string {
  const base = `${s.count > 1 ? `${s.count} ta ` : ''}${COLOR_NAMES[s.color]} ${SHAPE_NAMES[s.type]}`;
  return s.type === 'arrow' ? `${base} (${DIRECTION_NAMES[s.rotation] ?? ''})` : base;
}

export function generatePattern(rng: Rng, difficulty: GameDifficulty, count = 6): PatternInternal {
  const questions: PatternQuestionInternal[] = [];
  const seen = new Set<string>();
  let guard = 0;
  while (questions.length < count && guard++ < 200) {
    const p = plan(rng, difficulty);
    const item = (i: number): Shape => ({ type: p.type.at(i), color: p.color.at(i), rotation: p.rotation.at(i), count: p.count.at(i) });
    const items = Array.from({ length: SHOWN + 1 }, (_, i) => item(i));
    const answer = items[SHOWN]!;
    const key = items.map(shapeKey).join(';');
    if (seen.has(key)) continue;
    seen.add(key);

    // Distractors differ from the answer in exactly one attribute, so each is "almost right".
    const candidates: Shape[] = [];
    for (const v of p.type.alternatives) candidates.push({ ...answer, type: v });
    for (const v of p.color.alternatives) candidates.push({ ...answer, color: v });
    for (const v of p.rotation.alternatives) candidates.push({ ...answer, rotation: v });
    for (const v of p.count.alternatives) candidates.push({ ...answer, count: v });
    const unique = new Map<string, Shape>();
    for (const c of shuffle(rng, candidates)) if (shapeKey(c) !== shapeKey(answer)) unique.set(shapeKey(c), c);
    const distractors = [...unique.values()].slice(0, 3);
    if (distractors.length < 3) continue;

    const qid = `pt${questions.length + 1}`;
    const { options, correctOptionId } = withOptions(
      rng,
      qid,
      { shape: answer },
      distractors.map((shape) => ({ shape })),
    );
    const rules = [p.type.explain, p.color.explain, p.count.explain, p.rotation.explain].filter(Boolean).join(' ');
    questions.push({
      id: qid,
      sequence: [...items.slice(0, SHOWN), null],
      options,
      correctOptionId,
      explanation: `${rules} Demak, keyingisi — ${describeShape(answer)}.`,
    });
  }
  return { kind: 'pattern', questions };
}
