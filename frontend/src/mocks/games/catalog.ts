/**
 * DEV-ONLY stand-in for the admin-managed game catalogue (backend table `games`).
 * Copy lives here, not in the frontend, so instructions can later be edited by administrators.
 */
import type { GameCategory, GameDifficulty, GameKind } from '@/features/brain-games/types';

export interface CatalogGame {
  id: string;
  slug: string;
  kind: GameKind;
  title: string;
  description: string;
  category: GameCategory;
  difficulties: GameDifficulty[];
  durationMinutes: number;
  isActive: boolean;
  intro: { title: string; text: string };
  instructions: string[];
}

export const CATEGORIES: Array<{ id: GameCategory; title: string; description: string }> = [
  { id: 'memory', title: 'Xotira', description: 'Eslab qolish va diqqatni jamlash' },
  { id: 'logic', title: 'Mantiq', description: 'Naqsh va qonuniyatlarni topish' },
  { id: 'math', title: 'Matematika', description: 'Sonlar bilan aqlli oʻyinlar' },
  { id: 'attention', title: 'Diqqat', description: 'Kuzatuvchanlik va farqlarni koʻrish' },
  { id: 'spatial', title: 'Fazoviy fikrlash', description: 'Yoʻl topish va rejalashtirish' },
  { id: 'language', title: 'Soʻz va til', description: 'Soʻz boyligi va harflar' },
];

export const CATALOG: CatalogGame[] = [
  {
    id: 'game_memory',
    slug: 'xotira-kartalari',
    kind: 'memory',
    title: 'Xotira kartalari',
    description: 'Bir xil rasmli kartalarni juft-juft qilib toping.',
    category: 'memory',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 3,
    isActive: true,
    intro: { title: 'Xotirangizni sinab koʻrishga tayyormisiz?', text: 'Bir xil rasmlarni toping va barcha kartalarni oching!' },
    instructions: ['Ikkita kartani bosib oching.', 'Rasmlar bir xil boʻlsa, ular ochiq qoladi.', 'Har xil boʻlsa, kartalar yana yopiladi — joyini eslab qoling!'],
  },
  {
    id: 'game_missing_number',
    slug: 'yashiringan-son',
    kind: 'missing-number',
    title: 'Yashiringan son',
    description: 'Sonlar qatoridagi qonuniyatni toping va boʻsh joyni toʻldiring.',
    category: 'math',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 4,
    isActive: true,
    intro: { title: 'Sonlar sirini ochamizmi?', text: 'Qatordagi sonlar bir qoidaga boʻysunadi. Yashiringan sonni toping!' },
    instructions: ['Sonlar qatoriga diqqat bilan qarang.', 'Ular qanday oʻzgarayotganini toping: qoʻshilyaptimi, koʻpaytirilyaptimi?', 'Toʻrtta javobdan toʻgʻrisini tanlang.'],
  },
  {
    id: 'game_pattern',
    slug: 'naqsh-ustasi',
    kind: 'pattern',
    title: 'Naqsh ustasi',
    description: 'Shakllar qatori qanday davom etishini toping.',
    category: 'logic',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 4,
    isActive: true,
    intro: { title: 'Naqsh ustasi boʻlishga tayyormisiz?', text: 'Shakllar, ranglar va burilishlardagi qoidani toping — keyingisi qaysi?' },
    instructions: ['Shakllar qatoriga qarang: shakl, rang, son va yoʻnalish oʻzgarishi mumkin.', 'Qaysi qoida takrorlanayotganini toping.', 'Qatorni davom ettiradigan shaklni tanlang.'],
  },
  {
    id: 'game_odd_one_out',
    slug: 'ortiqchasini-top',
    kind: 'odd-one-out',
    title: 'Ortiqchasini toping',
    description: 'Guruhga mos kelmaydigan narsani aniqlang.',
    category: 'attention',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 3,
    isActive: false,
    intro: { title: 'Ortiqchasini topa olasizmi?', text: 'Bittasi guruhga mos emas. Qaysi biri?' },
    instructions: [],
  },
  {
    id: 'game_quick_math',
    slug: 'tez-hisob',
    kind: 'quick-math',
    title: 'Tez hisob',
    description: 'Ogʻzaki hisoblashni mashq qiling — 10 ta misol.',
    category: 'math',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 3,
    isActive: false,
    intro: { title: 'Hisoblashga tayyormisiz?', text: '10 ta qiziqarli misol sizni kutmoqda.' },
    instructions: [],
  },
  {
    id: 'game_maze',
    slug: 'labirint',
    kind: 'maze',
    title: 'Labirint',
    description: 'Doʻstingizni labirintdan olib chiqing.',
    category: 'spatial',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 4,
    isActive: false,
    intro: { title: 'Yoʻlni topa olasizmi?', text: 'Devorlardan oʻtib boʻlmaydi — chiqishni toping!' },
    instructions: [],
  },
  {
    id: 'game_word_search',
    slug: 'sozlar-qidiruvi',
    kind: 'word-search',
    title: 'Soʻzlar qidiruvi',
    description: 'Harflar orasiga yashiringan soʻzlarni toping.',
    category: 'language',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 5,
    isActive: false,
    intro: { title: 'Soʻz ovchisi boʻlamizmi?', text: 'Harflar orasidan soʻzlarni toping.' },
    instructions: [],
  },
];
