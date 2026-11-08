import type { GameResult } from '../types';

/** Supportive copy only: no shame, no comparison with others, no "you lost". */
export function completionMessage(result: Pick<GameResult, 'correctAnswers' | 'totalQuestions' | 'moves'>): { title: string; text: string } {
  if (result.moves !== null) {
    return { title: 'Barakalla! Barcha juftlarni topding!', text: 'Xotirang zo‘r ishladi. Har safar o‘ynaganingda u yanada kuchliroq bo‘ladi.' };
  }
  const ratio = result.totalQuestions > 0 ? result.correctAnswers / result.totalQuestions : 0;
  if (ratio >= 0.9) return { title: 'Barakalla! Ajoyib natija!', text: 'Sen bu topshiriqlarni juda yaxshi tushunding. Qiyinroq darajani sinab ko‘rasanmi?' };
  if (ratio >= 0.6) return { title: 'Barakalla! Ajoyib harakat qilding!', text: 'Har bir o‘yin bilan fikrlashing yanada tezroq va aniqroq bo‘lyapti.' };
  if (ratio >= 0.3) return { title: 'Zo‘r harakat!', text: 'Qiyin topshiriqlar — eng yaxshi mashq. Tushuntirishlarni eslab, yana bir bor urinib ko‘r.' };
  return { title: 'Yaxshi boshlanish!', text: 'Har bir urinish yangi narsa o‘rgatadi. Oson darajadan boshlab ko‘rsang ham bo‘ladi.' };
}

/** Immediate per-answer feedback lines, picked at random for variety. */
export const CORRECT_LINES = ['Barakalla!', 'Zoʻr! Aynan shunday!', 'Ajoyib! Topding!', 'Juda yaxshi!'];
export const WRONG_LINES = ['Hech gap emas, yana bir bor!', 'Deyarli! Mana qoida:', 'Yaxshi urinish! Endi bilasan:'];
export const randomLine = (lines: string[]) => lines[Math.floor(Math.random() * lines.length)]!;
