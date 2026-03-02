# Telegram Consulting Bot (Uzbek)

Ushbu loyiha O‘zbekistonlik talabalarga Yaponiyada o‘qish bo‘yicha ariza yig‘uvchi Telegram bot.

Bot imkoniyatlari:
- Foydalanuvchini bosqichma-bosqich savollar bilan olib boradi
- Har bosqichda progress ko‘rsatadi (`3/8 savol`)
- Yosh va yil uchun raqam tekshiradi
- Yakunda arizani formatlab, professional guruhga yuboradi
- `/start` bilan har doim qaytadan boshlash mumkin
- Railway uchun webhook rejimida ishlaydi (24/7)

## Fayllar
- `bot.py` - asosiy bot kodi (hammasi bitta faylda)
- `requirements.txt` - Python kutubxonalari
- `.env.example` - environment variable namunasi
- `Procfile` - Railway ishga tushirish komandasi

## 1) Bot yaratish (BotFather)
1. Telegram’da `@BotFather` ni oching.
2. `/newbot` yuboring.
3. Bot nomi kiriting (masalan: `Japan Consulting Bot`).
4. Username kiriting (masalan: `japan_consulting_uz_bot`).
5. BotFather sizga `BOT_TOKEN` beradi. Uni saqlab oling.

## 2) Professional guruh tayyorlash
1. Telegram’da private guruh yarating.
2. Yangi botingizni guruhga qo‘shing.
3. Botga xabar yuborish uchun uni admin qiling.

## 3) GROUP_CHAT_ID olish (eng oson usul)
1. Telegram’da `@RawDataBot` ni toping.
2. `@RawDataBot` ni professional guruhga qo‘shing.
3. Guruh ichida `@RawDataBot` ga `/start` yoki oddiy xabar yuboring.
4. JSON javob ichidan `"chat":{"id":-100...}` qiymatini toping.
5. Shu `-100...` ni `GROUP_CHAT_ID` sifatida ishlating.

Zaxira usul: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` URL orqali ham shu `chat.id` ni olish mumkin.

## 4) Lokal ishga tushirish (test uchun)
1. Kompyuteringizda Python 3.11+ o‘rnating.
2. Loyihani oching.
3. `.env.example` fayldan nusxa olib, nomini `.env` qiling.
4. `.env` ichiga quyidagilarni yozing:
   - `BOT_TOKEN=...`
   - `GROUP_CHAT_ID=-100...`
   - `WEBHOOK_BASE_URL=` (lokalda bo‘sh qoldirsa bo‘ladi)
5. Terminalda:

```bash
pip install -r requirements.txt
python bot.py
```

6. Telegram’da botga `/start` yuborib tekshiring.

## 5) Railway.app ga deploy qilish (24/7)

### 5.1 GitHub ga yuklash
1. GitHub’da yangi repo yarating.
2. Shu loyiha fayllarini repoga yuklang.

### 5.2 Railway loyiha yaratish
1. [Railway](https://railway.app/) ga kiring.
2. `New Project` -> `Deploy from GitHub repo` ni tanlang.
3. O‘zingiz yuklagan repni tanlang.

### 5.3 Domain olish
1. Railway project ichida `Settings` yoki `Networking` bo‘limiga kiring.
2. Public domain yarating (masalan: `https://your-app.up.railway.app`).

### 5.4 Environment variables qo‘shish
Railway project `Variables` bo‘limida quyidagilarni kiriting:
- `BOT_TOKEN` = BotFather token
- `GROUP_CHAT_ID` = `-100...`
- `WEBHOOK_BASE_URL` = Railway public domain (masalan `https://your-app.up.railway.app`)
- `WEBHOOK_SECRET` = ixtiyoriy xavfsizlik kaliti (masalan uzun random matn)

`PORT` ni Railway odatda avtomatik beradi.

### 5.5 Ishga tushirish
- `Procfile` ichida `web: python bot.py` bor.
- Deploy tugagach, bot webhook rejimida ishlaydi.

## 6) 24/7 ishlashi uchun muhim eslatma
- Railway’da doimiy ishlash uchun sleeping bo‘lmaydigan tarif/planni tanlang.
- Agar loyiha “sleep” bo‘lsa, bot javob berishda kechikadi.

## 7) Muammolar va yechimlar
- `BOT_TOKEN topilmadi`:
  - Railway yoki `.env` ga token kiritilmagan.
- Guruhga xabar bormayapti:
  - `GROUP_CHAT_ID` noto‘g‘ri
  - bot guruhga qo‘shilmagan yoki xabar yozish huquqi yo‘q
- Bot ishga tushmayapti:
  - `requirements.txt` install bo‘lganini tekshiring
  - Railway deploy loglarini tekshiring

## 8) Xavfsizlik
- Hech qachon `BOT_TOKEN` ni ommaga chiqarmang.
- Token oshkor bo‘lsa, BotFather’da yangi token oling (`/revoke`).

---
Agar xohlasangiz, keyingi bosqichda men sizga: admin panel, Google Sheets saqlash, CRM integratsiya yoki avtomatik follow-up funksiyasini ham qo‘shib beraman.
