Bilimdon — 10–14 yoshli o‘zbek bolalari uchun bilim, imtihon va mantiqiy o‘yinlar platformasi. Dizayn **mobile-first** (asosiy o‘lcham 360×800, 390×844 da ham tekshiriladi), keyin 1440px kompyuter. Ruhi — quvnoq va o‘yinsimon (Duolingo, Brilliant), lekin 13–14 yoshlilarga “chaqaloqcha” tuyulmaydi. Yengil, havodor, ixcham: ekranga ko‘p foydali ma’lumot sig‘adi, lekin tiqilinch emas.

## Matn va ovoz

- Barcha matnlar o‘zbek tilida, lotin yozuvida. Tutuq va o‘ belgisi uchun `ʻ` (U+02BB): “Oʻyinlar”, “toʻgʻri”; tutuq belgisi `ʼ`: “maʼlumot”.
- Bolaga “sen” deb, do‘stona murojaat: “Bugun 5 ta savol yech”, “Naqsh ustasi boʻlishga tayyormisan?”.
- Tugmalar fe’l bilan boshlanadi va natijani aytadi: “Imtihonni boshlash”, “Oʻyinni boshlash”, “Yana oʻynash”. “OK”, “Davom” ishlatilmaydi.
- Gaplar sarlavha registrida (faqat birinchi so‘z bosh harf bilan). BOSH HARFLAR faqat `overline` stilida: “KUNLIK MISSIYA”.
- Xato javobda hech qachon ayblamaymiz: “Hech gap emas, yana bir bor!”. To‘g‘ri javobda qisqa maqtov + mukofot: “Barakalla! +10 ⭐”.
- Raqamlar: “45 ta savol”, “60 daqiqa”, “38/45”, “5 kun”. Sana: “5-noyabr”.
- Emoji — faqat aksent: salomlashuvda 👋 va mukofot yonida ⭐. Seriya va ball chiplarida emoji emas, `fire` va `star` ikonkalari (Androidda bir xil ko‘rinadi).

## Rang

- Sahifa foni `bg`, kartalar `card` (oq/krem), iliq ikkinchi darajali kartalar `card-cream`. Ajratgichlar va progress izi `line`.
- Matn: asosiy `ink`, ikkinchi darajali `ink-2` (13px), eng xira `ink-3` (sana, faol bo‘lmagan nav). Uchalasi ham `bg` va `card` ustida ≥ 4.5:1.
- Brend yashili `brand` (#1F6F5F) — asosiy tugma, faol holat, progress. Uning ustida matn `on-brand`. Brend rangidagi matn `brand-ink`. Faol nav “pill” va ikkinchi darajali tugma `brand-soft`.
- Asosiy blok (hero) — `hero` fon, `on-hero` matn; qorong‘i rejimda `hero` xiraroq yashil, `brand` esa yorqinroq.
- `sun` — xatcho‘p, “Topshirish mumkin” belgisi; ustidagi matn `on-sun`.
- **Fan va yo‘nalish ranglari** — har biri uchtadan: `<x>` (ikonka, progress), `<x>-soft` (plita foni), `<x>-ink` (matn). Komponentlarda `is-<x>` klassi orqali ulanadi.
  - Matematika `math` (binafsha-ko‘k, Σ) · Mantiq/IQ `logic` (sariq-to‘q sariq, jumboq) · Ona tili va adabiyot `lang` (pushti, kitob)
  - O‘yin yo‘nalishlari: Xotira `memory` · Mantiq `logic` · Matematika `math` · Diqqat `attn` · Fazoviy fikrlash `spatial` · So‘z va til `lang`
- Motivatsiya: `streak` (🔥 seriya), `star` (⭐ ball) — `-soft` fon + `-ink` matn chipda.
- Javob holati: `success` / `danger` (+ `-soft`, `-ink`). **Doim ✓ yoki ✕ ikonkasi bilan** — rang yolg‘iz ma’no tashimaydi.
- Fokus halqasi: `focus`, 2px qattiq chiziq, 2px offset — har qanday yuzada ≥ 3:1.
- Barcha matn juftliklari ikkala rejimda WCAG AA dan o‘tadi (tokenlar izohida qaysi fon ustida ekani yozilgan).

## Shrift

Nunito (Google Fonts, 500–900). Bitta oila, og‘irlik bilan ierarxiya:

| stil | o‘lcham | qayerda |
| --- | --- | --- |
| `display` | 32/38, 900 | Faqat kompyuter sarlavhasi |
| `title-hero` | 22/28, 800 | Asosiy blok va sahifa sarlavhasi |
| `title-section` | 18/24, 800 | Bo‘lim sarlavhasi (kompyuterda 20px) |
| `title-card` | 15/20, 800 | Karta, ro‘yxat qatori |
| `body` | 15/22, 500 | Asosiy matn, savollar |
| `body-sm` | 13/18, 600 | Ikkinchi darajali ma’lumot, `ink-2` |
| `label` | 13/16, 800 | Chip, kichik tugma |
| `nav` | 11/14, 700 | Pastki menyu (faol: 800) |
| `overline` | 11/14, 800, +6% | Kategoriya belgisi |
| `stat` | 22/26, 900 | Ball, natija raqami |

12px dan kichik matn faqat `nav` va `overline` (ikkalasi ham 700+ qalinlikda).

## Masofa, radius, soya

- 4px setka: `space-1` 4 · `space-2` 8 · `space-3` 12 · `space-4` 16 · `space-6` 24.
- Telefon: sahifa chetlari `space-4`, kartalar orasi `space-3` (grid ichida 8px), bo‘limlar orasi `space-6`, karta ichi 12–16px.
- Radius: ikonka plitasi `radius-sm` (10), tugma `radius-md` (14), karta `radius-lg` (18), hero `radius-xl` (22), chip/avatar/progress `radius-full`.
- Soya: kartalar `shadow-sm`, hero va panellar `shadow-md` (ko‘p qatlamli, mayin). Asosiy tugma `shadow-press` — 4px qattiq pastki qirra (3D “bosiladigan”).
- Chap rangli chegara (left-border) va rang gradientli kartalar ishlatilmaydi.

## O‘lchamlar va qulaylik

- Bosiladigan maydon ≥ `hit-min` (44px) — ko‘rinishi kichik bo‘lsa ham ko‘rinmas hit-area bilan (`::after`).
- Asosiy tugma `control-lg` 48px, ikkinchi darajali `control-md` 40px, chip `control-sm` 28px.
- Ikonkalar `icon-md` 20px, navigatsiyada `icon-lg` 22px.
- Header `header-h` ≤ 56px, pastki menyu `nav-h` 60px + `env(safe-area-inset-bottom)`; sahifa kontentiga pastdan ≥ 96px bo‘shliq.
- Har bir ekranda **bitta** asosiy amal. Tafsilot va o‘yin kirish ekranlarida u pastda yopishgan (`bd-sticky`), bosh barmoq zonasida.

## Ikonkalar

Phosphor Duotone uslubidagi yumaloq ikonkalar: 2px chiziq + 22% shaffof to‘ldirish, `currentColor`. Bundle'dagi `Bilimdon.icon(name)` 40 ta ikonkani beradi; Reactda `@phosphor-icons/react` `weight="duotone"` bilan almashtiriladi. O‘yinlar bo‘limi — `game` (gamepad), kolba emas.

## Maskot

Yashil kitob — katta ko‘zli, sariq xatcho‘pli. Kayfiyatlar: `salom`, `ishora`, `oylayapti`, `xursand`, `hayron` (qarang: Mascot komponenti). Bir ekranda bitta maskot. Hero ichida 88–96px va doim tugmaning o‘ng tomonida, unga ishora qilib. Bo‘sh holatlarda `oylayapti`, natijada `xursand` + konfetti, xatodan keyin `hayron` + rag‘bat so‘zi. Maskot ranglari ikkala rejimda o‘zgarmaydi.

## Naqsh

Hero fonida tartibli naqsh: Σ, jumboq bo‘lagi, “Aa”, “?” — 96px setkada, oq, 9% shaffoflikda. Tasodifiy, burchakda kesilgan shakllar ishlatilmaydi.

## Harakat

- Tugma bosilganda `scale(.97)`; 3D tugmada qirra 3px pastga tushadi.
- Kartalar ketma-ket paydo bo‘ladi (`bd-rise`, 50ms qadam).
- Maskot qo‘l silkitadi, 🔥/⭐ ikonkalari vaqti-vaqti bilan yengil tebranadi (`bd-wiggle`).
- To‘g‘ri javob — “pop”, xato — “shake”, natijada konfetti.
- **Hammasi faqat `@media (prefers-reduced-motion: no-preference)` ichida.**

## Holatlar

Har bir ekran ikki holatda chiziladi: (a) yangi foydalanuvchi — 0 ball, 0 seriya, qulflangan nishonlar, “Kun savoli”; (b) faol foydalanuvchi — 38/45, 5 kunlik seriya, 2 ta ochilgan nishon, to‘lgan progresslar, “So‘nggi faoliyat”. Bo‘sh holat hech qachon quruq emas: maskot + bitta aniq amal + muqobil mashq.

## Kompyuter (≥ 1024px)

Pastki menyu chap yon panelga (248px) aylanadi, logo va maskot shu yerda. Kontent 2 ustun (1.6fr / 1fr), chetlar `space-10`, bloklar orasi `space-6`. Sahifa sarlavhasi `display`.

## React + Tailwind

`tokens.css` CSS o‘zgaruvchilarini beradi; Tailwind'da ularni nom bilan ulang:

```js
// tailwind.config.js
const v = (n) => `var(--${n})`;
module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    fontFamily: { sans: ['Nunito', 'system-ui', 'sans-serif'] },
    extend: {
      colors: Object.fromEntries(['bg','bg-tint','card','card-cream','line','ink','ink-2','ink-3','brand','brand-strong','brand-soft','brand-ink','on-brand','hero','on-hero','sun','on-sun',
        'math','math-soft','math-ink','logic','logic-soft','logic-ink','lang','lang-soft','lang-ink','memory','memory-soft','memory-ink','attn','attn-soft','attn-ink',
        'spatial','spatial-soft','spatial-ink','streak','streak-soft','streak-ink','star','star-soft','star-ink','success','success-soft','success-ink','danger','danger-soft','danger-ink','focus'].map(n => [n, v(n)])),
      borderRadius: { sm: v('radius-sm'), md: v('radius-md'), lg: v('radius-lg'), xl: v('radius-xl') },
      boxShadow: { sm: v('shadow-sm'), md: v('shadow-md'), press: v('shadow-press') },
      height: { 'control-lg': v('control-lg'), 'control-md': v('control-md'), nav: v('nav-h') },
    },
  },
};
```

Masalan, asosiy tugma: `h-control-lg rounded-md bg-brand text-on-brand shadow-press font-extrabold active:translate-y-[3px] active:shadow-none motion-safe:transition`. Komponentlar `components/bundle.css` dagi `bd-*` klasslari bilan bir xil tuzilishda — har bir komponent README'sida qaysi tokenlar ishlatilishi yozilgan.
