import { describe, expect, it } from 'vitest';
import { splitMath } from './richHtml';

describe('splitMath', () => {
  it('leaves plain text alone', () => {
    expect(splitMath('Oddiy matn')).toEqual([{ kind: 'text', value: 'Oddiy matn' }]);
  });

  it('finds inline formulas between text', () => {
    expect(splitMath('Hisoblang: $\\frac{1}{2}$ va tugat')).toEqual([
      { kind: 'text', value: 'Hisoblang: ' },
      { kind: 'math', latex: '\\frac{1}{2}', display: false },
      { kind: 'text', value: ' va tugat' },
    ]);
  });

  it('supports every delimiter the editor can produce', () => {
    expect(splitMath('$$a$$')).toEqual([{ kind: 'math', latex: 'a', display: true }]);
    expect(splitMath('\\[b\\]')).toEqual([{ kind: 'math', latex: 'b', display: true }]);
    expect(splitMath('\\(c\\)')).toEqual([{ kind: 'math', latex: 'c', display: false }]);
    expect(splitMath('$d$')).toEqual([{ kind: 'math', latex: 'd', display: false }]);
  });

  it('reads $$ as a display formula, not as two empty inline ones', () => {
    expect(splitMath('$$x^2$$ va $y$').map((s) => s.kind === 'math' && s.display)).toEqual([true, false, false]);
  });

  it('handles several formulas in one text', () => {
    const math = splitMath('$a$ + $b$').filter((s) => s.kind === 'math');
    expect(math).toHaveLength(2);
  });

  it('keeps an escaped dollar as a literal sign', () => {
    expect(splitMath('Narxi 5\\$ va 7\\$')).toEqual([{ kind: 'text', value: 'Narxi 5$ va 7$' }]);
  });

  it('does not treat a single dollar as a formula', () => {
    expect(splitMath('Narxi 5$ edi')).toEqual([{ kind: 'text', value: 'Narxi 5$ edi' }]);
  });

  it('does not let an inline formula run across lines', () => {
    expect(splitMath('5$\nva 7$')).toEqual([{ kind: 'text', value: '5$\nva 7$' }]);
  });

  it('keeps comparison signs inside a formula', () => {
    expect(splitMath('$a < b \\& c$')).toEqual([{ kind: 'math', latex: 'a < b \\& c', display: false }]);
  });
});
