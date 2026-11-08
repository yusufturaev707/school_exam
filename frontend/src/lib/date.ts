import dayjs from 'dayjs';

const MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];

/** "5-noyabr, 2026" */
export function formatDate(iso: string): string {
  const d = dayjs(iso);
  return `${d.date()}-${MONTHS[d.month()]}, ${d.year()}`;
}

/** Dizayn uslubi: "Bugun", "Kecha" yoki "1-noyabr" (yil — faqat boshqa yil boʻlsa). */
export function formatDay(iso: string): string {
  const d = dayjs(iso);
  const today = dayjs().startOf('day');
  if (d.isSame(today, 'day')) return 'Bugun';
  if (d.isSame(today.subtract(1, 'day'), 'day')) return 'Kecha';
  return d.year() === today.year() ? `${d.date()}-${MONTHS[d.month()]}` : `${d.date()}-${MONTHS[d.month()]}, ${d.year()}`;
}

/** "5-noyabr, 14:30" */
export function formatDateTime(iso: string): string {
  const d = dayjs(iso);
  return `${d.date()}-${MONTHS[d.month()]}, ${d.format('HH:mm')}`;
}
