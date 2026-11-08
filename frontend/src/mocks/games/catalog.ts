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
  { id: 'math', title: 'Matematika', description: 'Sonlar bilan aqlli o‘yinlar' },
  { id: 'attention', title: 'Diqqat', description: 'Kuzatuvchanlik va farqlarni ko‘rish' },
  { id: 'spatial', title: 'Fazoviy fikrlash', description: 'Yo‘l topish va rejalashtirish' },
  { id: 'language', title: 'So‘z va til', description: 'So‘z boyligi va harflar' },
];

export const CATALOG: CatalogGame[] = [
  {
    id: 'game_memory',
    slug: 'xotira-kartalari',
    kind: 'memory',
    title: 'Xotira kartalari',
    description: 'Bir xil rasmli kartalarni juft-juft qilib top.',
    category: 'memory',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 3,
    isActive: true,
    intro: { title: 'Xotirangni sinab ko‘rishga tayyormisan?', text: 'Bir xil rasmlarni top va barcha kartalarni och!' },
    instructions: ['Ikkita kartani bosib och.', 'Rasmlar bir xil bo‘lsa, ular ochiq qoladi.', 'Har xil bo‘lsa, kartalar yana yopiladi — joyini eslab qol!'],
  },
  {
    id: 'game_missing_number',
    slug: 'yashiringan-son',
    kind: 'missing-number',
    title: 'Yashiringan son',
    description: 'Sonlar qatoridagi qonuniyatni top va bo‘sh joyni to‘ldir.',
    category: 'math',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 4,
    isActive: true,
    intro: { title: 'Sonlar sirini ochamizmi?', text: 'Qatordagi sonlar bir qoidaga bo‘ysunadi. Yashiringan sonni top!' },
    instructions: ['Sonlar qatoriga diqqat bilan qara.', 'Ular qanday o‘zgarayotganini top: qo‘shilyaptimi, ko‘paytirilyaptimi?', 'To‘rtta javobdan to‘g‘risini tanla.'],
  },
  {
    id: 'game_pattern',
    slug: 'naqsh-ustasi',
    kind: 'pattern',
    title: 'Naqsh ustasi',
    description: 'Shakllar qatori qanday davom etishini top.',
    category: 'logic',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 4,
    isActive: true,
    intro: { title: 'Naqsh ustasi bo‘lishga tayyormisan?', text: 'Shakllar, ranglar va burilishlardagi qoidani top — keyingisi qaysi?' },
    instructions: ['Shakllar qatoriga qara: shakl, rang, son va yo‘nalish o‘zgarishi mumkin.', 'Qaysi qoida takrorlanayotganini top.', 'Qatorni davom ettiradigan shaklni tanla.'],
  },
  {
    id: 'game_odd_one_out',
    slug: 'ortiqchasini-top',
    kind: 'odd-one-out',
    title: 'Ortiqchasini top',
    description: 'Guruhga mos kelmaydigan narsani aniqla.',
    category: 'attention',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 3,
    isActive: false,
    intro: { title: 'Ortiqchasini topa olasanmi?', text: 'Bittasi guruhga mos emas. Qaysi biri?' },
    instructions: [],
  },
  {
    id: 'game_quick_math',
    slug: 'tez-hisob',
    kind: 'quick-math',
    title: 'Tez hisob',
    description: 'Og‘zaki hisoblashni mashq qil — 10 ta misol.',
    category: 'math',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 3,
    isActive: false,
    intro: { title: 'Hisoblashga tayyormisan?', text: '10 ta qiziqarli misol seni kutmoqda.' },
    instructions: [],
  },
  {
    id: 'game_maze',
    slug: 'labirint',
    kind: 'maze',
    title: 'Labirint',
    description: 'Do‘stingni labirintdan chiqishga olib bor.',
    category: 'spatial',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 4,
    isActive: false,
    intro: { title: 'Yo‘lni topa olasanmi?', text: 'Devorlardan o‘tib bo‘lmaydi — chiqishni top!' },
    instructions: [],
  },
  {
    id: 'game_word_search',
    slug: 'sozlar-qidiruvi',
    kind: 'word-search',
    title: 'So‘zlar qidiruvi',
    description: 'Harflar orasiga yashiringan so‘zlarni top.',
    category: 'language',
    difficulties: ['easy', 'medium', 'hard'],
    durationMinutes: 5,
    isActive: false,
    intro: { title: 'So‘z ovchisi bo‘lamizmi?', text: 'Harflar orasidan so‘zlarni top.' },
    instructions: [],
  },
];
