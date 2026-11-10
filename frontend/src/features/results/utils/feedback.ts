import type { SubjectCode } from '@/types/subject';

type Band = 'high' | 'mid' | 'growing';

export function band(percent: number): Band {
  if (percent >= 80) return 'high';
  if (percent >= 50) return 'mid';
  return 'growing';
}

/** Supportive, never labelling. Low results are framed as the next thing to explore. */
const SUBJECT_MESSAGES: Record<SubjectCode, Record<Band, string>> = {
  math: {
    high: 'Matematikada ajoyib natija koʻrsatdingiz!',
    mid: 'Matematikada yaxshi natija koʻrsatdingiz! Biroz mashq qilsangiz, yanada zoʻr boʻladi.',
    growing: 'Matematik masalalarni koʻproq yechib koʻrish foydali boʻladi. Siz albatta uddalaysiz!',
  },
  iq: {
    high: 'Mantiqiy fikrlashingiz juda zoʻr!',
    mid: 'Mantiqiy savollarda yaxshi harakat qildingiz!',
    growing: 'Mantiqiy savollarda yana biroz mashq qilish foydali boʻladi.',
  },
  language: {
    high: 'Ingliz tilida ajoyib natija koʻrsatdingiz! Excellent!',
    mid: 'Ingliz tilida yaxshi natija! Har kuni bir nechta yangi soʻz oʻrgansangiz, yanada zoʻr boʻladi.',
    growing: 'Ingliz tilida soʻzlar va oddiy gaplarni koʻproq takrorlash foydali boʻladi. Siz albatta uddalaysiz!',
  },
};

export function subjectMessage(subject: SubjectCode, percent: number): string {
  return SUBJECT_MESSAGES[subject][band(percent)];
}

/**
 * Overall headline by percent: >70% praise, 30–70% encouragement, <30% an honest, kind next step.
 * Never labels the child; never over-praises a low score.
 */
export function overallHeadline(percent: number): { title: string; text: string } {
  if (percent > 70) return { title: 'Zoʻr natija!', text: 'Siz juda yaxshi tayyorlangansiz. Shunday davom eting!' };
  if (percent >= 30) return { title: 'Yaxshi harakat!', text: 'Koʻp narsani bilasiz. Endi qaysi mavzularni mustahkamlash mumkinligini koʻrib chiqing.' };
  return { title: 'Boshlanishi bor — endi oʻsamiz!', text: 'Bu imtihon qaysi mavzularni takrorlash kerakligini koʻrsatdi. Xatolar ustida ishlasangiz, keyingi safar natija albatta yaxshiroq boʻladi.' };
}
