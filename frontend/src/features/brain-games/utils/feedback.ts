import type { GameResult } from '../types';

/** Supportive copy only: no shame, no comparison with others, no "you lost". */
export function completionMessage(result: Pick<GameResult, 'correctAnswers' | 'totalQuestions' | 'moves'>): { title: string; text: string } {
  if (result.moves !== null) {
    return { title: 'Barakalla! Barcha juftlarni topdingiz!', text: 'Xotirangiz zoʻr ishladi. Har safar oʻynaganingizda u yanada kuchliroq boʻladi.' };
  }
  const ratio = result.totalQuestions > 0 ? result.correctAnswers / result.totalQuestions : 0;
  if (ratio >= 0.9) return { title: 'Barakalla! Ajoyib natija!', text: 'Siz bu topshiriqlarni juda yaxshi tushundingiz. Qiyinroq darajani sinab koʻrasizmi?' };
  if (ratio >= 0.6) return { title: 'Barakalla! Ajoyib harakat qildingiz!', text: 'Har bir oʻyin bilan fikrlashingiz yanada tezroq va aniqroq boʻlmoqda.' };
  if (ratio >= 0.3) return { title: 'Zoʻr harakat!', text: 'Qiyin topshiriqlar — eng yaxshi mashq. Tushuntirishlarni eslab, yana bir bor urinib koʻring.' };
  return { title: 'Yaxshi boshlanish!', text: 'Har bir urinish yangi narsa oʻrgatadi. Oson darajadan boshlab koʻrsangiz ham boʻladi.' };
}

/** Immediate per-answer feedback lines, picked at random for variety. */
export const CORRECT_LINES = ['Barakalla!', 'Zoʻr! Aynan shunday!', 'Ajoyib! Topdingiz!', 'Juda yaxshi!'];
export const WRONG_LINES = ['Hech gap emas, yana bir bor!', 'Deyarli! Mana qoida:', 'Yaxshi urinish! Endi bilasiz:'];
export const randomLine = (lines: string[]) => lines[Math.floor(Math.random() * lines.length)]!;
