# Bilimdon dizayni — fayllar

- `demo/index.html` — bosiladigan demo. Brauzerda ochsangiz ishlaydi (internet kerak faqat Nunito shrifti uchun).
- `dizayn-tizimi/README.md` — brend kitobi: ranglar, shrift, masofalar, ikonkalar, maskot, harakat, React + Tailwind sozlamasi.
- `dizayn-tizimi/tokens.json` — barcha tokenlar (yorugʻ va qorongʻi rejim).
- `dizayn-tizimi/tokens.css` — shu tokenlar CSS oʻzgaruvchilari koʻrinishida; loyihaga birinchi boʻlib ulanadi.
- `dizayn-tizimi/components/bundle.css` — barcha komponent uslublari (`bd-*` klasslari).
- `dizayn-tizimi/components/bundle.js` — ikonkalar (`Bilimdon.icon`) va maskot (`Bilimdon.mascot`).
- `dizayn-tizimi/components/<Nom>/README.md` — har bir komponent qoidalari.
- `dizayn-tizimi/components/<Nom>/preview.html` — komponent namunasi. Bular dizayn tizimi sahifasi ichida ishlaydi; alohida ochsangiz `tokens.css`, `bundle.css` va `bundle.js` ni `<head>` ga qoʻshing.
- `PROMPT.md` — Claude'da shu dizaynni React + Tailwind'da qurish uchun prompt.

Oʻz sahifangizda ishlatish:

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito:wght@500;600;700;800;900&display=swap">
<link rel="stylesheet" href="dizayn-tizimi/tokens.css">
<link rel="stylesheet" href="dizayn-tizimi/components/bundle.css">
<script src="dizayn-tizimi/components/bundle.js"></script>
<div class="bd">
  <a class="bd-btn bd-btn--primary">Imtihonni boshlash</a>
  <span data-mascot="salom" data-size="96"></span>
</div>
```
