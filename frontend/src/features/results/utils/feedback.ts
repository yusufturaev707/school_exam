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
    high: 'Matematikada ajoyib natija ko‘rsatding!',
    mid: 'Matematikada yaxshi natija ko‘rsatding! Biroz mashq bilan yanada zo‘r bo‘ladi.',
    growing: 'Matematik masalalarni ko‘proq yechib ko‘rish foydali bo‘ladi. Sen albatta uddalaysan!',
  },
  iq: {
    high: 'Mantiqiy fikrlashing juda zo‘r!',
    mid: 'Mantiqiy savollarda yaxshi harakat qilding!',
    growing: 'Mantiqiy savollarda yana biroz mashq qilish foydali bo‘ladi.',
  },
  language: {
    high: 'Ingliz tilida ajoyib natija ko‘rsatding! Excellent!',
    mid: 'Ingliz tilida yaxshi natija! Har kuni bir nechta yangi so‘z o‘rgansang, yanada zo‘r bo‘ladi.',
    growing: 'Ingliz tilida so‘zlar va oddiy gaplarni ko‘proq takrorlash foydali bo‘ladi. Sen albatta uddalaysan!',
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
  if (percent > 70) return { title: 'Zoʻr natija!', text: 'Sen juda yaxshi tayyorlangansan. Shunday davom et!' };
  if (percent >= 30) return { title: 'Yaxshi harakat!', text: 'Koʻp narsani bilasan. Quyida qaysi mavzularni mustahkamlash mumkinligini koʻr.' };
  return { title: 'Boshlanishi bor — endi oʻsamiz!', text: 'Bu imtihon qaysi mavzularni takrorlash kerakligini koʻrsatdi. Xatolar ustida ishlasang, keyingi safar natija albatta yaxshiroq boʻladi.' };
}
