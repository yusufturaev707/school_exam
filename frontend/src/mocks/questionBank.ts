/**
 * DEV-ONLY MOCK DATA. Contains an answer key so the mock backend can score attempts.
 * This file is only reachable through the VITE_USE_MOCKS dynamic import and is excluded
 * from production bundles. Real questions and answers live exclusively on the backend.
 */
import type { ContentBlock } from '@/types/content';
import type { Question } from '@/features/examination/types';
import type { SubjectCode } from '@/types/subject';
import { colors, shapes, svgUri } from './svg';

interface MockQuestion extends Question {
  correct: string;
  explanation: ContentBlock[];
}

const t = (text: string): ContentBlock => ({ type: 'text', text });
const m = (latex: string): ContentBlock => ({ type: 'math', latex });

let n = 0;
function q(subject: SubjectCode, prompt: ContentBlock[], options: Array<string | ContentBlock[]>, correctIndex: number, explanation: string, passage?: ContentBlock[]): MockQuestion {
  n += 1;
  const id = `q${String(n).padStart(2, '0')}`;
  const labels = ['A', 'B', 'C', 'D'];
  // Deterministically rotate options so the correct answer isn't always "A".
  // (Options that are themselves letters — "which figure: A/B/C/D" — keep their order.)
  const lettersOnly = options.every((o) => typeof o === 'string' && /^[A-D]$/.test(o));
  const shift = lettersOnly ? 0 : (n * 7) % options.length;
  const rotated = options.map((_, i) => options[(i - shift + options.length) % options.length]!);
  const correctPos = (correctIndex + shift) % options.length;
  return {
    id,
    number: n,
    subject,
    type: 'single_choice',
    prompt,
    passage: passage ?? null,
    options: rotated.map((o, i) => ({ id: `${id}-${labels[i]!.toLowerCase()}`, label: labels[i]!, content: typeof o === 'string' ? [t(o)] : o })),
    correct: `${id}-${labels[correctPos]!.toLowerCase()}`,
    explanation: [t(explanation)],
  };
}

/* ---------- illustrations ---------- */
const rectangleImg = svgUri(
  320,
  190,
  `<rect x="60" y="40" width="200" height="110" rx="4" fill="#E9EEFF" stroke="${colors.BLUE}" stroke-width="4"/>
   <text x="160" y="30" text-anchor="middle" font-size="20" font-weight="800" fill="${colors.INK}">8 sm</text>
   <text x="40" y="102" text-anchor="middle" font-size="20" font-weight="800" fill="${colors.INK}">5 sm</text>`,
);
const triangleImg = svgUri(
  320,
  210,
  `<path d="M40 180L280 180L120 30Z" fill="#FFF1D9" stroke="${colors.AMBER}" stroke-width="4" stroke-linejoin="round"/>
   <text x="70" y="170" font-size="20" font-weight="800" fill="${colors.INK}">50°</text>
   <text x="232" y="170" font-size="20" font-weight="800" fill="${colors.INK}">70°</text>
   <text x="112" y="72" font-size="22" font-weight="800" fill="${colors.TEAL}">?</text>`,
);
const shapeSequenceImg = svgUri(
  400,
  80,
  [shapes.circle(36, 40), shapes.square(100, 40), shapes.triangle(164, 42), shapes.circle(228, 40), shapes.square(292, 40), shapes.question(360, 40)].join(''),
);
const oddOneImg = svgUri(
  400,
  110,
  [shapes.triangle(50, 50), shapes.triangle(150, 50, colors.PINK), shapes.square(250, 50), shapes.triangle(350, 50, colors.BLUE)].join('') +
    ['A', 'B', 'C', 'D'].map((l, i) => `<text x="${50 + i * 100}" y="100" text-anchor="middle" font-size="18" font-weight="800" fill="${colors.INK}">${l}</text>`).join(''),
);
const gridImg = svgUri(
  240,
  240,
  [
    [2, 4, 6],
    [3, 6, 9],
    [4, 8, null],
  ]
    .flatMap((row, r) =>
      row.map(
        (v, c) =>
          `<rect x="${10 + c * 76}" y="${10 + r * 76}" width="68" height="68" rx="12" fill="${v === null ? '#fff' : '#E5F4F0'}" stroke="${v === null ? colors.INK : colors.TEAL}" stroke-width="3" ${v === null ? 'stroke-dasharray="6 5"' : ''}/>
           <text x="${44 + c * 76}" y="${56 + r * 76}" text-anchor="middle" font-size="28" font-weight="800" fill="${colors.INK}">${v ?? '?'}</text>`,
      ),
    )
    .join(''),
);
const arrowsImg = svgUri(400, 80, [shapes.arrow(40, 40, 0), shapes.arrow(120, 40, 90), shapes.arrow(200, 40, 180), shapes.question(290, 40)].join(''));
const dotsImg = svgUri(
  400,
  110,
  [1, 3, 6]
    .map((count, i) => {
      const rows = count === 1 ? 1 : count === 3 ? 2 : 3;
      let out = '';
      for (let r = 0; r < rows; r++) for (let c = 0; c <= r; c++) out += `<circle cx="${60 + i * 110 + (c - r / 2) * 22}" cy="${30 + r * 22}" r="8" fill="${colors.TEAL}"/>`;
      return out;
    })
    .join('') + shapes.question(350, 52),
);

const passage: ContentBlock[] = [
  t(
    'Nilufar bahorda bobosi bilan hovliga o‘rik ko‘chati ekdi. Har kuni maktabdan qaytgach, ko‘chatga suv quyar, atrofidagi o‘tlarni yulardi. Yoz kelib, ko‘chat bo‘yi Nilufarning beligacha yetdi.\n\nBir kuni qattiq shamol turdi. Nilufar yugurib chiqib, ko‘chatni qoziqqa bog‘lab qo‘ydi. Bobosi uni maqtab: “Daraxt ham xuddi bola kabi g‘amxo‘rlikni sevadi”, — dedi.',
  ),
];

export const QUESTIONS: MockQuestion[] = [
  /* ---------- Matematika ---------- */
  q('math', [t('Ifodaning qiymatini toping:'), m('\\frac{3}{4} + \\frac{1}{8}')], [[m('\\frac{7}{8}')], [m('\\frac{4}{12}')], '1', [m('\\frac{5}{8}')]], 0, '3/4 = 6/8, demak 6/8 + 1/8 = 7/8.'),
  q('math', [t('Hisoblang: $2^5 - 3^2$')], ['23', '1', '16', '41'], 0, '2⁵ = 32, 3² = 9, 32 − 9 = 23.'),
  q('math', [t('Hisoblang:'), m('\\sqrt{81} + \\sqrt{16}')], ['13', '25', '10', '97'], 0, '√81 = 9, √16 = 4, jami 13.'),
  q('math', [t('Tenglamani yeching: $3x + 7 = 25$')], ['x = 6', 'x = 4', 'x = 8', 'x = 18'], 0, '3x = 25 − 7 = 18, x = 6.'),
  q('math', [t('To‘g‘ri to‘rtburchakning perimetrini toping.'), { type: 'image', src: rectangleImg, alt: 'Tomonlari 8 sm va 5 sm bo‘lgan to‘g‘ri to‘rtburchak', width: 320, height: 190 }], ['26 sm', '40 sm', '13 sm', '30 sm'], 0, 'P = 2 · (8 + 5) = 26 sm.'),
  q('math', [t('240 ning 15% i nechaga teng?')], ['36', '24', '30', '48'], 0, '240 · 0,15 = 36.'),
  q('math', [t('Uchburchakning noma’lum burchagini toping.'), { type: 'image', src: triangleImg, alt: 'Ikki burchagi 50° va 70° bo‘lgan uchburchak', width: 320, height: 210 }], ['60°', '50°', '70°', '80°'], 0, 'Uchburchak burchaklari yig‘indisi 180°: 180 − 50 − 70 = 60°.'),
  q('math', [t('Hisoblang: $1{,}2 \\cdot 0{,}5$')], ['0,6', '6', '0,06', '1,7'], 0, '12 · 5 = 60, verguldan keyin ikki xona: 0,60.'),
  q('math', [t('Qaysi kasr eng kichik?')], [[m('\\frac{2}{3}')], [m('\\frac{3}{5}')], [m('\\frac{5}{8}')], [m('\\frac{7}{12}')]], 3, '7/12 ≈ 0,58 — qolganlaridan kichik.'),
  q('math', [t('Avtomobil 3 soatda 180 km yo‘l bosdi. Uning tezligi qancha?')], ['60 km/soat', '90 km/soat', '540 km/soat', '50 km/soat'], 0, 'v = 180 : 3 = 60 km/soat.'),
  q('math', [t('Hisoblang: $(-4) \\cdot (-6) + (-10)$')], ['14', '−34', '34', '−14'], 0, '(−4)·(−6) = 24, 24 − 10 = 14.'),
  q('math', [t('Tomoni 7 sm bo‘lgan kvadratning yuzi qancha?')], ['49 sm²', '28 sm²', '14 sm²', '21 sm²'], 0, 'S = 7 · 7 = 49 sm².'),
  q('math', [t('35 ning $\\frac{2}{5}$ qismini toping.')], ['14', '7', '10', '21'], 0, '35 : 5 · 2 = 14.'),
  q('math', [t('Ketma-ketlikni davom ettiring: 3, 7, 11, 15, …')], ['19', '18', '20', '21'], 0, 'Har bir son oldingisidan 4 ga katta.'),
  q('math', [t('Radiusi 5 sm bo‘lgan aylana uzunligini toping ($\\pi \\approx 3{,}14$).'), m('C = 2\\pi r')], ['31,4 sm', '15,7 sm', '78,5 sm', '10 sm'], 0, 'C = 2 · 3,14 · 5 = 31,4 sm.'),

  /* ---------- Mantiq (IQ) ---------- */
  q('iq', [t('Qatorni davom ettiring: 2, 4, 8, 16, …')], ['32', '24', '20', '64'], 0, 'Har bir son ikki barobar ortadi.'),
  q('iq', [t('Qatorni davom ettiring: 1, 1, 2, 3, 5, 8, …')], ['13', '11', '10', '16'], 0, 'Har bir son oldingi ikki sonning yig‘indisi: 5 + 8 = 13.'),
  q('iq', [t('So‘roq belgisi o‘rnida qaysi shakl bo‘lishi kerak?'), { type: 'image', src: shapeSequenceImg, alt: 'Doira, kvadrat, uchburchak, doira, kvadrat va so‘roq belgisi', width: 400, height: 80 }], ['Uchburchak', 'Doira', 'Kvadrat', 'Yulduz'], 0, 'Shakllar doira → kvadrat → uchburchak tartibida takrorlanadi.'),
  q('iq', [t('Qaysi shakl boshqalaridan farq qiladi?'), { type: 'image', src: oddOneImg, alt: 'A, B va D — uchburchaklar, C — kvadrat', width: 400, height: 110 }], ['A', 'B', 'C', 'D'], 2, 'Faqat C kvadrat, qolganlari uchburchak.'),
  q('iq', [t('Barcha mushuklar — hayvon. Mosh — mushuk. Demak…')], ['Mosh — hayvon', 'Barcha hayvonlar — mushuk', 'Mosh — it', 'Hech narsa deyish mumkin emas'], 0, 'Mosh mushuklar guruhida, mushuklar esa hayvonlar guruhida.'),
  q('iq', [t('Qo‘l : qo‘lqop = oyoq : ?')], ['Paypoq', 'Shim', 'Shlyapa', 'Ro‘mol'], 0, 'Qo‘lqop qo‘lga, paypoq oyoqqa kiyiladi.'),
  q('iq', [t('Jadvaldagi qonuniyatni toping. So‘roq o‘rnida qaysi son turadi?'), { type: 'image', src: gridImg, alt: 'Jadval: 2, 4, 6; 3, 6, 9; 4, 8 va so‘roq belgisi', width: 240, height: 240 }], ['12', '10', '16', '9'], 0, 'Har bir qatorda sonlar birinchi sonning 1, 2, 3 barobari: 4, 8, 12.'),
  q('iq', [t('Harflar qatorini davom ettiring: A, C, E, G, …')], ['I', 'H', 'J', 'K'], 0, 'Har safar bitta harf tashlab ketiladi.'),
  q('iq', [t('Nuqtalar soni qanday o‘zgaryapti? Keyingi rasmda nechta nuqta bo‘ladi?'), { type: 'image', src: dotsImg, alt: '1, 3 va 6 ta nuqtadan iborat uchburchaklar', width: 400, height: 110 }], ['10', '9', '12', '8'], 0, 'Har gal yangi qator qo‘shiladi: 1, 1+2, 1+2+3, 1+2+3+4 = 10.'),
  q('iq', [t('Qaysi raqam ko‘zguda (chap-o‘ng) o‘zgarmasdan ko‘rinadi?')], ['8', '2', '4', '7'], 0, '8 raqami ikki tomoni bir xil — simmetrik.'),
  q('iq', [t('Kubning nechta qirrasi bor?')], ['12', '6', '8', '24'], 0, 'Kubda 12 ta qirra, 6 ta yoq va 8 ta uch bor.'),
  q('iq', [t('Ali Validan baland. Vali Solidan baland. Kim eng past?')], ['Soli', 'Ali', 'Vali', 'Aniqlab bo‘lmaydi'], 0, 'Ali > Vali > Soli, demak Soli eng past.'),
  q('iq', [t('5 ta mashina 5 daqiqada 5 ta o‘yinchoq yasaydi. 100 ta mashina 100 ta o‘yinchoqni necha daqiqada yasaydi?')], ['5 daqiqa', '100 daqiqa', '20 daqiqa', '1 daqiqa'], 0, 'Har bir mashina 5 daqiqada 1 ta o‘yinchoq yasaydi.'),
  q('iq', [t('Strelka qaysi tomonga buriladi?'), { type: 'image', src: arrowsImg, alt: 'Strelkalar: yuqoriga, o‘ngga, pastga va so‘roq belgisi', width: 400, height: 80 }], ['Chapga', 'Yuqoriga', 'O‘ngga', 'Pastga'], 0, 'Strelka har safar soat mili bo‘yicha chorak aylanadi.'),
  q('iq', [t('Qatorni davom ettiring: 3, 9, 27, …')], ['81', '54', '36', '30'], 0, 'Har bir son 3 ga ko‘paytiriladi.'),

  /* ---------- Ona tili va adabiyot ---------- */
  q('language', [t('Nilufar ko‘chatni qachon ekdi?')], ['Bahorda', 'Yozda', 'Kuzda', 'Qishda'], 0, 'Matnning birinchi gapida aytilgan.', passage),
  q('language', [t('Shamol turganda Nilufar nima qildi?')], ['Ko‘chatni qoziqqa bog‘ladi', 'Uyga yashirindi', 'Ko‘chatga suv quydi', 'Bobosini chaqirdi'], 0, 'Matnning ikkinchi xatboshisida yozilgan.', passage),
  q('language', [t('Bobosining so‘zlari qanday asosiy fikrni ifodalaydi?')], ['G‘amxo‘rlik har bir tirik narsaga kerak', 'Daraxt ekish qiyin', 'Shamol xavfli', 'Bolalar ko‘p o‘ynashi kerak'], 0, 'Bobo daraxtni bolaga o‘xshatib, g‘amxo‘rlik muhimligini aytmoqda.', passage),
  q('language', [t('Qaysi so‘z ot (narsa nomi)?')], ['kitob', 'chiroyli', 'yugurmoq', 'tez'], 0, '“Kitob” — narsa nomi, “nima?” so‘rog‘iga javob beradi.'),
  q('language', [t('“Katta” so‘zining zid ma’noli so‘zi (antonimi) qaysi?')], ['kichik', 'ulkan', 'baland', 'keng'], 0, 'Katta — kichik.'),
  q('language', [t('“Chiroyli” so‘zining ma’nodoshi (sinonimi) qaysi?')], ['go‘zal', 'xunuk', 'katta', 'tez'], 0, 'Chiroyli — go‘zal.'),
  q('language', [t('Qaysi so‘z to‘g‘ri yozilgan?')], ['maktab', 'mahtab', 'maktap', 'matkab'], 0, 'To‘g‘ri yozilishi: maktab.'),
  q('language', [t('“Daftar” so‘zining ko‘plik shakli qaysi?')], ['daftarlar', 'daftarlik', 'daftarchi', 'daftarim'], 0, 'Ko‘plik -lar qo‘shimchasi bilan yasaladi.'),
  q('language', [t('“Alpomish” qanday janrdagi asar?')], ['Doston', 'Masal', 'Topishmoq', 'Maqol'], 0, '“Alpomish” — o‘zbek xalq qahramonlik dostoni.'),
  q('language', [t('“O‘tkan kunlar” romanining muallifi kim?')], ['Abdulla Qodiriy', 'Oybek', 'G‘afur G‘ulom', 'Cho‘lpon'], 0, 'Roman Abdulla Qodiriy tomonidan yozilgan.'),
  q('language', [t('So‘roq gap oxiriga qaysi tinish belgisi qo‘yiladi?')], ['?', '.', '!', ','], 0, 'So‘roq gaplar so‘roq belgisi bilan tugaydi.'),
  q('language', [t('“O‘zbekiston” so‘zi nechta bo‘g‘indan iborat?')], ['4', '3', '5', '2'], 0, 'O‘z-be-kis-ton — 4 bo‘g‘in.'),
  q('language', [t('“Bolalar bog‘da o‘ynashdi” gapidagi fe’lni toping.')], ['o‘ynashdi', 'bolalar', 'bog‘da', 'fe’l yo‘q'], 0, '“O‘ynashdi” — harakatni bildiradi.'),
  q('language', [t('Gapni to‘ldiring: “Men har kuni … o‘qiyman.”')], ['kitob', 'tez', 'qizil', 'baland'], 0, '“Kitob o‘qiyman” — ma’noli gap.'),
  q('language', [t('Alisher Navoiy qaysi asrda yashab ijod qilgan?')], ['XV asr', 'XII asr', 'XVIII asr', 'XX asr'], 0, 'Navoiy 1441–1501-yillarda yashagan.'),
];

export function publicQuestions(): Question[] {
  return QUESTIONS.map(({ correct: _c, explanation: _e, ...rest }) => rest);
}
