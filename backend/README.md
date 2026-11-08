# Bilimdon — backend

Django + DRF + PostgreSQL. Frontend bilan shartnoma: [`frontend/docs/api-contract.md`](../frontend/docs/api-contract.md).
Maydon nomlari uchun manba — frontenddagi zod sxemalari (`frontend/src/features/*/types`).

## Ishga tushirish

Kerak bo'ladi: Python 3.12+, PostgreSQL (5432-port) va unda `school_exam` bazasi.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env                     # POSTGRES_USER va POSTGRES_PASSWORD'ni yozing
python manage.py migrate
python manage.py seed_demo                 # demo o'quvchilar, imtihon, QR tokenlar
python manage.py createsuperuser           # /admin/ uchun
python manage.py runserver 8000
```

Keyin boshqa terminalda: `cd frontend; npm run dev`. Vite `/api` so'rovlarini 8000-portga yo'naltiradi.

| JSHSHIR | O'quvchi | Holati |
|---|---|---|
| `12345678901234` | Aziz | imtihon ochiq |
| `23456789012345` | Malika | imtihon ochiq |
| `34567890123456` | Bobur | imtihon topshirilgan, tarixi bor |

QR: `demo-qr-valid-7f3a9c2e1b4d` (bir martalik), `demo-qr-expired-0c8e2a9f71`, `demo-qr-used-5b1d7e3c9a20`.
Hammasini boshidan boshlash: `python manage.py seed_demo --reset`.

## Tekshirish

```powershell
pytest                                # DB foydalanuvchisida CREATEDB huquqi kerak (test_school_exam yaratiladi)
ruff check .
node scripts/verify_contract.mjs      # ishlab turgan serverni frontendning zod sxemalari bilan tekshiradi
```

`verify_contract.mjs` oldidan `seed_demo --reset` qiling va server ishlab tursin. Frontend yoki backendda maydon
nomi o'zgarsa, shu skript birinchi bo'lib aytadi.

## Tuzilma

```
config/          settings (bitta fayl, farqlar faqat .env orqali), urls
apps/core/       umumiy: xato formati, CSRF middleware, UUID model, serializer yordamchilari
apps/schools/    Region, District, School, Classroom, admin filtrlari, yangi o'quv yiliga o'tkazish
apps/accounts/   Pupil, QR token, kirish/chiqish, rate limit, Excel/CSV'dan import (pupil_import.py)
apps/exams/      imtihon, urinish, javoblar, baholash, natijalar, dashboard
apps/games/      o'yinlar: generatorlar, sessiyalar, kunlik topshiriq, yutuqlar
apps/demo/       seed_demo (faqat DEBUG'da ishlaydi)
tests/           pytest
```

Har bir app ichida qatlamlar bir xil:

| Fayl | Vazifasi | Nima bo'lmasligi kerak |
|---|---|---|
| `views.py` | kirishni tekshirish, servisni chaqirish, javob qaytarish | biznes qoida |
| `services.py` | ma'lumotni o'zgartiradigan **hamma** qoida | HTTP, `request` |
| `selectors.py` | o'qish so'rovlari, N+1 siz | ma'lumotni o'zgartirish¹ |
| `serializers.py` | snake_case ↔ camelCase chegarasi | hisob-kitob |

¹ Bitta ongli istisno: `finalize_overdue_attempts` — pastga qarang.

**Yangi endpoint qo'shish tartibi:** model → service/selector → serializer → view → `urls.py` → test.

## Qabul qilingan qarorlar va sabablari

| Qaror | Nega | Rad etilgan variant |
|---|---|---|
| Django session (HttpOnly cookie) | Shartnoma shuni talab qiladi, frontend token ko'rmaydi | JWT: cookie bilan ishlaganda foydasi yo'q, chaqirib olish qiyin |
| `Pupil` alohida model | O'quvchida parol va admin huquqi yo'q | `auth.User`: keraksiz maydonlar, xavfli aralashuv |
| Ierarxiyada `PROTECT` | Viloyatni o'chirib yuborish o'quvchi va natijalarni yo'qotmasin; o'chirish o'rniga `status` | `CASCADE` |
| `status` pastga ta'sir qiladi | Maktab o'chirilsa, uning o'quvchilari kira olmaydi | Faqat o'quvchi statusini tekshirish |
| Savol HTML sifatida saqlanadi, formula `$...$` matn | Editor erkin, API blok formatini saqlab qoladi | Formula muharriri plagini: pullik yoki qo'shimcha bog'liqlik |
| HTML saqlashda `nh3` bilan tozalanadi | HTML bolalar brauzerida ochiladi. `RichTextField` ichida, shuning uchun admin ham, import ham undan o'tadi | Faqat admin formasida tozalash |
| Rasm savol matni ichida, base64 WebP | Savol bitta yozuv: alohida fayl zaxirasi yo'q, imtihondan oldin nomini taxmin qilib ochiladigan `/media/` fayl yo'q. Saqlashda 1600px gacha kichraytiriladi, EXIF o'chiriladi, 300 KB dan oshmaydi | `/media/` fayl: ochiq URL, alohida zaxira, ishlatilmay qolgan fayllar |
| JSHSHIR HMAC hash ko'rinishida saqlanadi | Bu bolaning shaxsiy raqami. Baza sizib chiqsa ham ochilmaydi | Ochiq saqlash |
| Faqat PostgreSQL | Imtihon xavfsizligi `SELECT FOR UPDATE`ga tayanadi, SQLite buni e'tiborsiz qoldiradi | SQLite'da dev: bu xatolarni yashirardi |
| Celery yo'q, cron + "keyingi murojaatda" | Bitta davriy vazifa uchun broker, worker va beat ortiqcha | Celery |
| camelCase serializerda ochiq yoziladi | `firstName`ni frontend va backendda bir xil grep qilish mumkin | camelCase kutubxonasi: `answers` kabi dict kalitlariga ham tegadi |
| Natija yakunlanganda saqlab qo'yiladi | Keyin savol tuzatilsa, bola olgan ball o'z-o'zidan o'zgarmaydi | Har safar qayta hisoblash |
| Yutuqlar saqlanmaydi, tarixdan hisoblanadi | Saqlangan qiymat tarix bilan ajralib qolmaydi | Alohida jadval |
| `Idempotency-Key` saqlanmaydi | Qulf va status tekshiruvi allaqachon "faqat bir marta"ni kafolatlaydi | Kalitlar jadvali |
| Rate limit: IP 300/min, identifikator 10/min | Butun maktab bitta IP ortida, sinf bir daqiqada kiradi | Mock'dagi 10/min per IP: sinfni bloklardi |

## Eng muhim qoidalar (o'zgartirishdan oldin o'qing)

**Vaqt faqat serverda.** `expires_at` boshlaganda hisoblanadi. Muddat o'tgach `PUT answers` 409 qaytaradi.
Yo'lda qolgan javoblar `submit` orqali yana `EXAM_GRACE_SECONDS` davomida qabul qilinadi.

**Brauzer yopilsa ham imtihon yakunlanadi.** `finalize_overdue_attempts` ikki joydan chaqiriladi: cron orqali
hamma uchun va o'quvchining har bir o'qish so'rovi boshida. `selectors.py`dagi yagona yozish shu.

**Har bir yozish urinish qatorini qulflaydi** (`_lock_own_attempt`). Shuning uchun javob yakunlangandan keyin kirib
qola olmaydi va urinish ikki marta yakunlanmaydi. Qulf bitta qatorda, o'quvchilar bir-birini kutmaydi.
`tests/test_concurrency.py` buni haqiqiy parallel tranzaksiyalar bilan tekshiradi. Qulfni olib tashlasangiz, testlar yiqiladi.

**"Faqat bir marta" kafolatlarini baza beradi.** Bitta urinish, bitta kunlik bonus, kuniga bitta javob:
bularning hammasi `UniqueConstraint`. Koddagi `if` parallel so'rovlardan himoya qilmaydi.

**To'g'ri javoblar sizib chiqmasin.** `QuestionSerializer` va `OptionSerializer`ga `is_correct`, `explanation`
qo'shmang. O'yin kontenti faqat `services.public_content` orqali chiqadi.

**Boshqa o'quvchining ma'lumoti** har doim 404, 403 emas: mavjudligi ham oshkor bo'lmasin.

**JSHSHIR** javobda, logda va cache kalitida bo'lmasligi kerak.

## Tuzilma: viloyatdan o'quvchigacha

```
Region (name, number, status)
 └─ District (region, name, number, status)
     └─ School (district, name, number, status)
         └─ Classroom (school, number, category, name, count, status, graduated_year)
             └─ Pupil (classroom, last_name, first_name, middle_name, imie, photo_url, status)
```

- **API nomlari:** frontend kontrakti `student` va `jshshir` so'zlarini ishlatadi, ular o'zgarmagan. Backend ichida `Pupil` va `imie` (JSHSHIR).
- **`Classroom.count`:** rejadagi o'quvchilar soni, admin kiritadi. Haqiqiy son ro'yxatda alohida ko'rinadi.
- **`Classroom.name`:** bo'sh qoldirilsa, avtomatik `5-A`.
- **`School.number`:** ixtiyoriy, chunki ayrim maktablarda faqat nom bor.
- **`Classroom.category`:** faqat lotin harfi. Kirillcha "А" lotincha "A"ga o'xshaydi, lekin boshqa harf: ro'yxatda
  bir-biridan farqlab bo'lmaydigan ikkita "5-A" paydo bo'lardi.
- **`Classroom.graduated_year`:** bitirgan sinf. U arxivda qoladi (natijalar uchun), lekin "11-A" nomini band qilmaydi.

## Imtihon kimga ko'rinadi

Imtihon sahifasidagi **"Kimga"** bo'limi (`ExamTarget`). Bitta qator bitta qoida:

| Qatorda tanlangan | Kim ko'radi |
|---|---|
| Viloyat / tuman / maktab / sinf | shu joydagi hamma o'quvchi |
| Joy + sinf raqami (masalan tuman + 9) | shu tumandagi 9-sinflar |
| Faqat sinf raqami | butun mamlakatdagi 9-sinflar |

- **Bir nechta qator:** birortasi mos kelsa, o'quvchi imtihonni ko'radi.
- **Bir qatorda bitta joy:** viloyat → tuman → maktab tartibida to'ldirsa bo'ladi. Ular bir-biriga mos bo'lsa,
  eng kichigi (masalan, maktab) saqlanadi. Mos bo'lmasa (maktab boshqa tumanda), xato ko'rsatiladi.
  Bir nechta maktab uchun bir nechta qator qo'shing.
- **Qatorsiz imtihonni hech kim ko'rmaydi.** Ataylab shunday: unutilgan qadam imtihonni butun mamlakatga emas, hech kimga
  ko'rsatmaydi. Admin bunday imtihonni saqlaganda ogohlantirish chiqadi, ro'yxatda "Hech kimga" deb yoziladi.
- **Boshlangan imtihon yo'qolmaydi:** o'quvchi boshqa sinfga o'tsa yoki qoidalar o'zgarsa ham, boshlagan yoki topshirgan
  imtihoni ro'yxatida qoladi.
- **Kod:** `Exam.objects.visible_to(pupil)`. Ro'yxat ham, `start` ham shuni ishlatadi, shuning uchun biriktirilmagan
  imtihonni ID orqali ham boshlab bo'lmaydi (404).

## O'quvchilarni Excel'dan yuklash

Maktab sahifasi → **"O'quvchilarni yuklash (Excel)"**. Shu sahifada namuna fayl bor.

- **Ustunlar:** `Sinf, Familiya, Ism, Otasining ismi, JSHSHIR`. Yuqorida sarlavha qatori bo'lishi mumkin, ustunlar tartibi
  ixtiyoriy. Format: `.xlsx` yoki UTF-8 `.csv` (`;` yoki `,`), ko'pi bilan 5000 qator.
- **Ikki qadam:** fayl to'liq tekshiriladi va nima o'zgarishi ko'rsatiladi, "Tasdiqlash" bosilgandagina saqlanadi.
  Bitta qatorda xato bo'lsa, hech narsa saqlanmaydi.
- **Bor o'quvchi** (shu JSHSHIR bilan) yangilanadi. U boshqa maktabda bo'lsa, shu maktabga o'tkaziladi va oldindan
  alohida ro'yxatda ko'rsatiladi. Faylda yo'q o'quvchilarga va o'quvchining `status`iga tegilmaydi.
- **JSHSHIR** sessiyada ham saqlanmaydi: tekshiruv va tasdiqlash orasida faqat hash turadi.
- **Excel xatolari aniq aytiladi:** JSHSHIR `3,12E+13` ko'rinishiga aylangan bo'lsa yoki sinf harfi kirillcha bo'lsa.

## Yangi o'quv yili

Maktablar ro'yxati → maktablarni belgilang (yoki filtr + "hammasini tanlash") → **"Keyingi o'quv yiliga o'tkazish"**.
Avval nima bo'lishi ko'rsatiladi, keyin tasdiqlanadi.

- **O'quvchilar emas, sinflar ko'chadi:** `5-A` → `6-A` o'quvchilari bilan birga. Nomi raqam bilan boshlansa, u ham
  o'zgaradi (`5-A (IT)` → `6-A (IT)`), qo'lda yozilgan boshqa nomlarga tegilmaydi.
- **11-sinflar bitiradi:** `graduated_year` yoziladi, `status` o'chadi. O'quvchilar kira olmaydi, natijalari saqlanadi.
  Ular sinflar va o'quvchilar ro'yxatida "Bitirganlar" filtri bilan ko'rinadi.
- **Bir yilda bir marta:** `School.last_promoted_year` ikki marta bosishdan himoya qiladi. Xato bilan o'tkazilgan bo'lsa,
  sinflarni qo'lda tuzating, qayta o'tkazish kerak bo'lsa, maktab sahifasida shu maydonni tozalang.
- **1-sinflar:** o'tkazishdan keyin bo'sh qoladi. Yangi 1-sinflarni Excel'dan yuklash qulay, yo'q sinflar o'zi yaratiladi.
- **Kod:** `apps/schools/services.py`. Sinflar katta raqamdan kichigiga qarab o'tadi, shuning uchun "maktabda bitta 6-A"
  qoidasi oraliqda ham buzilmaydi. Import ham, o'tkazish ham maktab qatorini bloklaydi, ular bir vaqtda ishlamaydi.

## Savol yozish (admin)

Savollar → Qo'shish. Matn, javoblar va izoh text editorda yoziladi: qalin, ro'yxat, jadval, rasm yuklash.
Rasm "Rasm qo'shish" tugmasi bilan yuklanadi (JPG, PNG, GIF, WebP, 10 MB gacha). U siqilib WebP qilinadi va savol
matnining ichiga `data:image/webp;base64,...` bo'lib yoziladi, alohida fayl saqlanmaydi. Boshqa saytdagi rasm havolasi yoki
Word'dan nusxalangan rasm qabul qilinmaydi: saqlashda xato chiqadi, rasmni faylga saqlab yuklang. Import JSON'ida ham
rasm shunday `data:` URI bo'lishi kerak.
Formulalar `$` belgilari orasida LaTeX'da yoziladi:

| Yoziladi | Natija |
|---|---|
| `$\frac{3}{4}$` | kasr |
| `$x^2$`, `$a_1$` | daraja, indeks |
| `$\sqrt{16}$` | ildiz |
| `$a \cdot b$`, `$a \leq b$`, `$90^\circ$` | ko'paytirish, kichik-teng, gradus |
| `$$\sum_{i=1}^{n} i$$` | alohida qatorda, markazda |
| `5\$` | oddiy dollar belgisi |

Saqlash va davom ettirish bosilgach, sahifada **"O'quvchi ko'radigan ko'rinish"** chiqadi. Formulada xato bo'lsa, u yerda
qizil rangda ko'rinadi: savolni e'lon qilishdan oldin shuni tekshiring.

Editor sozlamalari: `settings.py`, `CKEDITOR_5_CONFIGS`. `Autoformat` va `TextTransformation` ataylab o'chirilgan, ular
yozish paytida `1/2`ni `½`ga aylantirib, LaTeX'ni buzadi. Ularni yoqmang.

### Har bir o'quvchiga o'z tartibi

Imtihonda **"savollar tartibini aralashtirish"** va **"javob variantlarini aralashtirish"** belgilansa, savollar to'plami
hammaga bir xil, lekin har bir o'quvchiga tartib boshqacha tushadi:

- Fanlar (bo'limlar) tartibi saqlanadi. Fan ichida savollar **qiyinlik darajasi** bo'yicha guruhlanadi (oson → o'rta →
  qiyin) va har bir guruh ichida aralashtiriladi. Daraja ko'rsatilmagan savollar fan ichida erkin aralashadi.
- Variantlar ham aralashadi va harflar qaytadan A, B, C, D bo'lib qo'yiladi, ya'ni javob kaliti har kimda har xil.
- Tartib imtihon boshlanganda bir marta tuziladi va urinishda saqlanadi (`ExamAttempt.layout`). Keyin imtihon tahrirlansa
  ham o'quvchi ko'rgan tartib va uning javob kaliti o'zgarmaydi. Yangi qo'shilgan savol shu fanning oxiriga tushadi.
- Ball variant id'si bo'yicha hisoblanadi, harf bo'yicha emas, shuning uchun aralashtirish natijaga ta'sir qilmaydi.
- O'quvchining shaxsiy javob kaliti: **Urinishlar → o'quvchi → "Javob kaliti"** (savol №, fan, daraja, to'g'ri javob,
  o'quvchi javobi). Bahsli natijani shu yerda tekshirish mumkin.

Variantlarda "Yuqoridagilarning hammasi" kabi joyiga bog'liq javoblar yozmang: aralashganda ma'nosini yo'qotadi.

### Tayyor test: 4-sinf bitiruvchilari uchun diagnostika

`content/diagnostika_4_sinf.py`: 30 ta savol (matematika, mantiqiy fikrlash, ona tili, har biridan 10 ta: 3 oson,
4 o'rta, 3 qiyin), 9 tasi rasmli. Rasmlar SVG bo'lib skriptning o'zida chiziladi. O'zgartirish uchun skriptni tahrirlab,
JSON'ni qayta yarating va import qiling:

```powershell
python content/diagnostika_4_sinf.py
python manage.py import_exam content/diagnostika-4-sinf.json
```

Import qilingan test e'lon qilinmagan bo'ladi va barcha 4-sinflarga biriktiriladi. Javoblarni ko'rsatish o'chiq, chunki
savollar hammaga bir xil: oldin tugatganlar javoblarni keyingilarga yetkazib qo'yishi mumkin.

## Admin vazifalari

- **Imtihon yuklash:** `python manage.py import_exam fayl.json --publish`. Format namunasi: `apps/demo/data/exam.json`.
  Fayl xato bo'lsa, hech narsa saqlanmaydi. Keyin adminda "Kimga" bo'limini to'ldiring, aks holda uni hech kim ko'rmaydi.
- **Ro'yxatlar:** Viloyatlar → Tumanlar → Maktablar → Sinflar. Har bir sahifada quyi darajani shu yerning o'zida qo'shsa bo'ladi.
- **O'quvchi qo'shish:** ko'p bo'lsa, Excel'dan (yuqoriga qarang). Bir nechta bo'lsa, sinf sahifasida. JSHSHIR faqat yoziladi, keyin ko'rsatilmaydi. Qidiruvda to'liq 14 raqam ishlaydi.
- **Filtrlar:** viloyat tanlansa tuman, tuman tanlansa maktab ochiladi. Natijalar ro'yxatida ham ishlaydi.
- **QR chiptalar:** o'quvchilarni belgilang (masalan, sinf bo'yicha filtrlab) → "QR chiptalar yaratish".
  Muddatni tanlang (5 daqiqa, 1 soat, 1/3/7 kun), keyin chop etish sahifasi ochiladi: A4 varaqda 12 ta chipta,
  har birida ism, sinf, maktab va QR kod. Kod ichida havola bor: `QR_LOGIN_URL#t=<token>`. O'quvchi telefon kamerasini
  kodga qaratadi, havola ochiladi va u tizimga kiradi. Kompyuterda saytdagi "QR orqali kirish" skaneri ham shu kodni o'qiydi.
  `QR_LOGIN_URL` frontend'ning `/qr` sahifasi (masalan `https://bilimdon.uz/qr`). `DJANGO_DEBUG=True` bo'lsa,
  standart qiymati `http://localhost:5173/qr`. Telefonda sinash uchun kompyuterning tarmoqdagi manzilini yozing:
  `http://192.168.x.x:5173/qr` (vite'ni `--host` bilan ishga tushiring). Token `#` dan keyin turadi, shuning uchun
  u hech qaysi serverga va logga bormaydi.
  Chipta bir martalik. Kod faqat shu sahifada bo'ladi, qayta ochib bo'lmaydi: yo'qolsa, yangisini yarating.
  Bir martada ko'pi bilan 1000 ta. Kira olmaydigan (o'chirilgan, bitirgan) o'quvchilar tashlab ketiladi.
  Kerak bo'lsa, CSV fayl ham tanlash mumkin. Faqat o'quvchini tahrirlash huquqi borlar yarata oladi.
- **Qayta topshirish:** Urinishlar → "Qayta topshirishga ruxsat berish". Urinish va natija o'chiriladi.
- **O'yinlar va kun savollari:** adminda tahrirlanadi. Faqat generatori bor o'yinni faollashtirish mumkin
  (`apps/games/generators.py`, `GENERATORS`). Frontendda ham shu tur uchun engine bo'lishi kerak.

## Production

`.env`da: `DJANGO_DEBUG=False`, yangi `DJANGO_SECRET_KEY`, `JSHSHIR_HASH_KEY`, `POSTGRES_*`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, `REDIS_URL`, `NUM_PROXIES`.

> `JSHSHIR_HASH_KEY`ni bir marta yarating va ishonchli saqlang. U o'zgarsa yoki yo'qolsa, hech bir o'quvchi kira olmaydi.

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn config.wsgi:application --workers 4 --bind 127.0.0.1:8000
```

Cron:

```cron
* * * * *  cd /app && python manage.py finalize_expired_attempts
0 3 * * *  cd /app && python manage.py purge_stale_game_sessions && python manage.py clearsessions
```

- Frontend va `/api` **bitta domenda** bo'lishi shart (cookie shunga tayanadi, CORS ochilmagan). Nginx `/api`, `/admin`,
  `/ckeditor5` (muharrirdan rasm yuklash) va `/static`ni gunicorn'ga, qolganini frontend build'iga yo'naltiradi.
  Savol rasmlari bazada, `/media` papkasi yo'q.
- So'rov hajmi: rasmli savol formasi katta bo'ladi (Django 16 MB gacha qabul qiladi). Nginx'da `/admin` va `/ckeditor5`
  uchun `client_max_body_size 16m`, `/api` uchun `1m` qo'ying: o'quvchi API'siga katta so'rov kerak emas.
- Nginx'da gzip yoqing. Savollar (rasmlari bilan) imtihon boshida bir marta yuklanadi, keyin har daqiqada faqat
  kichik holat (`?questions=0`, bir necha KB) so'raladi.
- Redis production'da shart: usiz har bir worker rate limitni alohida sanaydi.
