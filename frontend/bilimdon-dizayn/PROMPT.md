# Bilimdon — Claude uchun prompt

Quyidagi matnni Claude'ga (claude.ai yoki Claude Code) yuboring. Yaxshiroq natija uchun shu papkadagi `dizayn-tizimi/tokens.css`, `dizayn-tizimi/components/bundle.css`, `dizayn-tizimi/components/bundle.js` va `demo/index.html` fayllarini ham biriktiring — shunda Claude dizaynni noldan oʻylab topmaydi, aynan shu dizayn tizimidan foydalanadi.

---

"Bilimdon" — 10–14 yoshli oʻzbek bolalari uchun bilim, imtihon va mantiqiy oʻyinlar platformasi. Biriktirilgan dizayn tizimi (tokens.css, bundle.css, bundle.js) va demo (index.html) asosida saytni **React + Tailwind**da qurib ber. Dizaynni oʻzgartirma — ranglar, oʻlchamlar va komponentlar aynan biriktirilgan fayllardagidek boʻlsin. Barcha matnlar oʻzbek tilida, lotin yozuvida (oʻ, gʻ uchun `ʻ` belgisi).

## Dizayn qoidalari (qisqacha)

- **Mobile-first:** asosiy oʻlcham 360×800, 390×844 da ham ishlasin; ≥1024px da chap yon panel va 2 ustunli kontent.
- **Rang:** CSS oʻzgaruvchilari `tokens.css` dan. Brend `--brand` (#1F6F5F), fon `--bg`, karta `--card`, matn `--ink` / `--ink-2` / `--ink-3`. Fanlar: Matematika `--math` (Σ), Mantiq/IQ `--logic` (jumboq), Ona tili `--lang` (kitob); yoʻnalishlar: `--memory`, `--attn`, `--spatial`. Har biri `-soft` (fon) va `-ink` (matn) juftligi bilan. Qorongʻi rejim: `data-theme="dark"`.
- **Shrift:** Nunito. Asosiy matn 15px/500, ikkinchi darajali 13px/600, boʻlim sarlavhasi 18px/800, hero sarlavhasi 22px/800, menyu yozuvi 11px/700.
- **Masofa:** 4px setka (4/8/12/16/24). Sahifa chetlari 16px, kartalar orasi 12px, boʻlimlar orasi 24px.
- **Radius:** ikonka plitasi 10, tugma 14, karta 18, hero 22, chip 999px.
- **Tugmalar:** asosiy 48px, 3D pastki qirra (`--shadow-press`), bosilganda `scale(.97)`; ikkinchi darajali 40px. Bosiladigan maydon har doim ≥ 44px.
- **Ikonkalar:** Phosphor Duotone (`@phosphor-icons/react`, `weight="duotone"`), 20px, menyuda 22px. Oʻyinlar boʻlimi — gamepad.
- **Maskot:** yashil kitob (`bundle.js` dagi `Bilimdon.mascot(mood)`), kayfiyatlar: salom, ishora, oylayapti, xursand, hayron. Bir ekranda bitta.
- **Harakat:** kartalar ketma-ket paydo boʻlishi, maskot qoʻl silkitishi, 🔥/⭐ tebranishi, toʻgʻri javobda “pop”, xatoda “shake”. Hammasi `prefers-reduced-motion` ni hurmat qilsin.
- **Kontrast:** WCAG AA. Toʻgʻri/xato javob rang bilan birga ✓/✕ belgisi bilan koʻrsatilsin.

## Sahifalar

1. **Bosh sahifa:** ixcham header (avatar + “Salom, Aziz! 👋”, oʻngda 🔥 seriya va ⭐ ball chiplari) → imtihon hero (≤35% ekran, maskot tugmaga ishora qiladi) → kunlik missiya (progress halqasi, “+20 ⭐”) → 3 ustunli fan kartalari → 4 nishonli “Yutuqlarim” → “Kun savoli” (yangi foydalanuvchi) yoki “Soʻnggi faoliyat” (faol foydalanuvchi) → pastki menyu.
2. **Imtihonlar:** filtr chiplari, “Ochiq / Kelgusi / Topshirilgan” boʻlimlari.
3. **Imtihon tafsiloti:** 3 statistika plitasi, fanlar roʻyxati, “Qanday ishlaydi?” 3 qadam, pastda yopishgan tugma.
4. **Oʻyinlar laboratoriyasi:** bugungi topshiriq, statistika, 6 yoʻnalish 3×2 gridda, oʻyinlar roʻyxati, “Tez orada” (kichik va xira).
5. **Oʻyin kirish:** illyustratsiya, 3 qadam, daraja segmenti (Oson/Oʻrtacha/Qiyin), pastda yopishgan “Oʻyinni boshlash”.
6. **Oʻyin jarayoni:** progress, savol markazda, 2×2 javoblar, maskot pufagida qisqa ragʻbat.
7. **Oʻyin natijasi:** konfetti, xursand maskot, ball/urinish/vaqt, yangi nishon, “Yana oʻynash”.
8. **Statistika, Yutuqlar (3 ustunli nishon gridi), Natijalar (boʻsh va toʻla holat), Profil** (daraja + XP, seriya, eng yaxshi natijalar, sozlamalar).

Pastki menyu: Bosh sahifa, Imtihon, Oʻyinlar, Natijalar, Profil — faol boʻlim yumshoq “pill” fonda, safe-area hisobga olingan.

## Natija

- `tailwind.config.js` — ranglar, radius, soyalar `tokens.css` oʻzgaruvchilariga ulangan.
- Har bir komponent alohida fayl: `Button`, `Chip`, `Card`, `SubjectCard`, `ProgressRing`, `ProgressBar`, `Badge`, `AppHeader`, `BottomNav`, `ExamHero`, `MissionCard`, `QuestionCard`, `GameCard`, `StatTile`, `Mascot`.
- Sahifalar React Router bilan; maʼlumotlar hozircha namunaviy (mock) — “yangi” va “faol” foydalanuvchi holatlari bilan.
- Avval Bosh sahifani toʻliq qur, keyin qolganlarini.
