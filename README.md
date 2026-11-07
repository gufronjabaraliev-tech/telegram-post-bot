# 🚀 Telegram Post & Schedule Mini App (`@Almuraadmin_bot`)

Telegram kanallar va guruhlarga 1 dan 10 tagacha rasm yuklab, formatlangan matn, interaktiv reaksiyalar (like/dislike), ulashish (share), izohlar (comments) va maxsus havolalar bilan post joylash, rejalashtirish hamda **shablonlar asosida doimiy avto-post chiqarish** imkoniyatiga ega zamonaviy Telegram Mini App (TMA).

---

## 🌟 Asosiy imkoniyatlar

1. **📸 1 dan 10 tagacha rasm yuklash**:
   - Drag & drop yoki fayl tanlash orqali birdaniga 10 tagacha rasm yuklash.
   - Rasmlarni oldindan ko'rish (thumbnails), birma-bir o'chirish.
   - Ko'p rasm tanlanganda Telegramda chiroyli albom (media group) sifatida chiqariladi.

2. **✍️ Post matni va formatlash (Rich Text)**:
   - **Qalin** (`<b>`), *Kursiv* (`<i>`), <u>Tag chizilgan</u> (`<u>`), <s>Ustidan chizilgan</s> (`<s>`), `Kod` (`<code>`), 🔗 Havolalar (`<a href="...">`).
   - Belgilar soni hisoblagichi (1024 ta rasm bo'lsa, 4096 ta faqat matn bo'lsa).

3. **⚙️ Post komplektatsiyalari (Interaktiv tugmalar)**:
   - **👍 Loyiha / Reaksiyalar**: O'quvchilar post ostida emoji bosib ovoz berishi mumkin (👍, ❤️, 🔥, 👏, 👎 va h.k.). Ovozlar soni real vaqtda yangilanadi.
   - **↗️ Postni ulashish (Share)**: O'quvchilar postni do'stlari yoki boshqa guruhlarga 1 marta bosish bilan ulashishi uchun maxsus tugma.
   - **💬 Izohlar (Comments)**: Kanal muhokama guruhi yoki chatiga to'g'ridan-to'g'ri o'tuvchi tugma.
   - **🔗 Maxsus havola tugmalari (URL Buttons)**: Sayt, boshqa kanal yoki botlarga o'tuvchi ixtiyoriy tugmalar qo'shish imkoniyati.
   - **📌 Kanalga qadash (Pin)** va **🔕 Tovushsiz yuborish (Silent)**.

4. **📑 Post shablonlari & Doimiy Avto-post (YANGI!)**:
   - Reusable shablonlar yaratish (masalan: "Ertalabki xabar", "Kunlik maslahat", "Reklama").
   - **Dinamik teglar**: `{sana}`, `{vaqt}`, `{kun}`, `{oy}`, `{yil}` — post chiqqanda avtomatik joriy sana va vaqtga aylanadi!
   - **Doimiy davriylik**:
     - *Har kuni belgilangan soatda* (masalan, har kuni 09:00 da).
     - *Har X soatda bir marta* (masalan, har 3 soatda).
     - *Har X daqiqada bir marta*.
   - Shablonni 1 bosish bilan yoqish/to'xtatish (Pause/Resume), zudlik bilan chiqarish yoki muharrirga ko'chirib ishlatish.

5. **⏰ Postni rejalashtirish (Scheduler)**:
   - "⚡ Hozir joylash" — postni darhol kanalga chop etadi.
   - "📅 Rejalashtirish" — sana va vaqtni tanlab qo'ysangiz, server vaqt yetib kelganda o'zi avtomatik tarzda kanalga joylaydi.

6. **👁️ Jonli Telegram ko'rinishi (Live Preview)**:
   - Post kanalga yuborilishidan oldin Telegramda qanday ko'rinishini Mini App ichida real vaqtda ko'rsatib turadi.

---

## 🛠️ Jonli ish holati

- **Bot:** [@Almuraadmin_bot](https://t.me/Almuraadmin_bot)
- **Mini App HTTPS havolasi:** `https://partial-feeding-baker-discovery.trycloudflare.com`
- **Mahalliy port:** `http://localhost:8000`

Ilovani qayta ishga tushirish uchun [`run.bat`](file:///c:/Users/user/Desktop/Ali/run.bat) faylini bosish kifoya.
