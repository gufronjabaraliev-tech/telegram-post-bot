import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp

from app.config import BOT_TOKEN, WEBAPP_URL
from app.database import (
    save_channel,
    get_user_channels,
    toggle_post_reaction,
    get_post,
    find_channel_owner,
    find_post_by_channel_message
)
from app.publisher import refresh_post_markup
from app.telegram_api import (
    set_bot_commands,
    set_menu_button,
    send_message,
    answer_callback_query,
    check_bot_channel_admin,
    get_chat
)

logger = logging.getLogger(__name__)

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def handle_start(chat_id: int, user_id: int, username: str):
    text = (
        f"Assalomu alaykum, <b>{username or 'Foydalanuvchi'}</b>! 👋\n\n"
        "🚀 <b>Telegram Post & Schedule Mini App</b> ga xush kelibsiz!\n\n"
        "Ushbu bot va Mini App orqali:\n"
        "• 📢 <b>Kanallaringizni ro'yxatdan tanlab</b> botni 1 bosishda admin qilishingiz mumkin\n"
        "• 📸 <b>1 dan 10 tagacha rasm</b> bilan albom postlar yaratishingiz\n"
        "• ✍️ Boyitilgan matn va reaksiyalar (Like/Dislike) qo'shishingiz\n"
        "• ⏰ Postlarni <b>avtomatik rejalashtirish yoki doimiy shablonlar</b> bo'yicha chiqarishingiz\n"
        "• 🔔 <b>Postlaringizga izoh (kommentariya) yozilganda</b> darhol bot orqali bildirishnoma olishingiz mumkin!\n\n"
        "Boshlash uchun pastdagi tugmalardan foydalaning:"
    )

    # Inline keyboard for instant WebApp launch
    inline_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "📱 Mini Appni ochish",
                    "web_app": {"url": WEBAPP_URL}
                }
            ],
            [
                {
                    "text": "📢 Kanal qo'shish (Admin qilish)",
                    "url": f"https://t.me/Almuraadmin_bot?startchannel=admin&admin=post_messages+edit_messages+delete_messages"
                },
                {
                    "text": "👥 Guruh qo'shish",
                    "url": f"https://t.me/Almuraadmin_bot?startgroup=admin&admin=post_messages+delete_messages"
                }
            ],
            [
                {
                    "text": "ℹ️ Yo'riqnoma",
                    "callback_data": "action_help"
                }
            ]
        ]
    }

    # Reply keyboard with native Telegram RequestChat (shows user's own channels and groups list!)
    reply_keyboard = {
        "keyboard": [
            [
                {
                    "text": "📢 O'z kanalimni tanlash (Botni admin qilish)",
                    "request_chat": {
                        "request_id": 101,
                        "chat_is_channel": True,
                        "bot_is_member": False,
                        "bot_administrator_rights": {
                            "can_post_messages": True,
                            "can_edit_messages": True,
                            "can_delete_messages": True
                        }
                    }
                }
            ],
            [
                {
                    "text": "👥 O'z guruhimni tanlash (Botni admin qilish)",
                    "request_chat": {
                        "request_id": 102,
                        "chat_is_channel": False,
                        "bot_is_member": False,
                        "bot_administrator_rights": {
                            "can_post_messages": True,
                            "can_delete_messages": True
                        }
                    }
                }
            ],
            [
                {
                    "text": "📱 Mini Appni ochish",
                    "web_app": {"url": WEBAPP_URL}
                }
            ]
        ],
        "resize_keyboard": True
    }

    await send_message(str(chat_id), text, reply_markup=reply_keyboard)
    # Also send inline action buttons
    await send_message(str(chat_id), "Mini App yoki kanal qo'shish:", reply_markup=inline_markup)

async def handle_help(chat_id: int):
    help_text = (
        "📖 <b>Botdan foydalanish bo'yicha yo'riqnoma:</b>\n\n"
        "1. <b>Kanal yoki Guruhni ulash (2 xil usul):</b>\n"
        "   • <b>Eng oson usul:</b> Pastdagi <b>'📢 O'z kanalimni tanlash'</b> tugmasini bosing. Telegram o'z kanallaringiz ro'yxatini ko'rsatadi, birini tanlasangiz bot avtomatik admin bo'ladi!\n"
        "   • <b>Username orqali:</b> Kanalingiz nomini (masalan: <code>@mening_kanalim</code>) botga yuboring.\n\n"
        "2. <b>Post tayyorlash va rejalashtirish:</b>\n"
        "   • <b>📱 Mini Appni ochish</b> tugmasini bosing.\n"
        "   • 1 dan 10 tagacha rasm, matn va Like/Share/Izoh tugmalarini qo'shing.\n"
        "   • Postni hozir yoki rejalashtirilgan vaqtda chiqaring.\n\n"
        "3. <b>Doimiy Shablonlar (Avto-post):</b>\n"
        "   • Mini Appdagi <b>'📑 Shablonlar'</b> bo'limida har kuni yoki har bir necha soatda avtomatik post chiqaruvchi jadval yarating.\n\n"
        "4. <b>Izohlardan xabardor bo'lish:</b>\n"
        "   • Kanalingizdagi postlarga biror kishi izoh (kommentariya) yozganda, bot sizga darhol izoh matni va havolasi bilan xabar beradi!"
    )
    await send_message(str(chat_id), help_text)

async def handle_chat_shared(msg: Dict[str, Any]):
    """Handles native chat selection from KeyboardButtonRequestChat."""
    chat_id = msg["chat"]["id"]
    from_user = msg.get("from", {})
    user_id = from_user.get("id", chat_id)
    chat_shared = msg.get("chat_shared", {})
    shared_chat_id = chat_shared.get("chat_id")

    if not shared_chat_id:
        return

    logger.info(f"Foydalanuvchi {user_id} chatni uladi: {shared_chat_id}")

    # Fetch chat info
    info = await get_chat(str(shared_chat_id))
    title = f"Kanal {shared_chat_id}"
    identifier = str(shared_chat_id)
    if info.get("ok"):
        res = info["result"]
        title = res.get("title", title)
        username = res.get("username")
        if username:
            identifier = f"@{username}"

    # Save to user channels
    save_channel(user_id, identifier, title=title)

    reply_markup = {
        "inline_keyboard": [
            [{"text": "🚀 Mini Appda post yaratish", "web_app": {"url": WEBAPP_URL}}]
        ]
    }
    await send_message(
        str(chat_id),
        f"✅ <b>{title}</b> muvaffaqiyatli ulandi va saqlandi!\n\n"
        f"📌 Identifikator: <code>{identifier}</code>\n"
        f"Bot administrator huquqiga ega bo'ldi.\n\n"
        f"Endi ushbu kanal Mini Appdagi kanallaringiz ro'yxatida avtomatik chiqadi!",
        reply_markup=reply_markup
    )

async def check_and_notify_comment(msg: Dict[str, Any]):
    """Detects when someone writes a comment in a channel's discussion and alerts the post creator."""
    reply_to = msg.get("reply_to_message")
    if not reply_to:
        return

    chat = msg.get("chat", {})
    chat_type = chat.get("type", "")

    # Discussion comments occur in groups / supergroups
    if chat_type not in ("supergroup", "group"):
        return

    from_user = msg.get("from", {})
    sender_id = from_user.get("id")
    sender_name = from_user.get("first_name", "Foydalanuvchi")
    sender_uname = f"@{from_user['username']}" if from_user.get("username") else ""
    comment_text = msg.get("text") or msg.get("caption") or "[Rasm / Fayl]"

    post_owner_id = None
    channel_title = chat.get("title", "Kanal")
    channel_identifier = ""
    post_preview = ""

    # Case 1: Reply to forwarded channel message
    fwd_chat = reply_to.get("forward_from_chat")
    fwd_msg_id = reply_to.get("forward_from_message_id")

    if fwd_chat:
        channel_id_num = fwd_chat.get("id")
        channel_title = fwd_chat.get("title", channel_title)
        channel_uname = fwd_chat.get("username")
        channel_identifier = f"@{channel_uname}" if channel_uname else str(channel_id_num)

        if fwd_msg_id:
            matched_post = find_post_by_channel_message(channel_identifier, fwd_msg_id)
            if matched_post:
                post_owner_id = matched_post.get("user_id")
                post_preview = matched_post.get("text") or ""

        if not post_owner_id:
            post_owner_id = find_channel_owner(channel_identifier)

    # Case 2: Direct reply to post message in group
    if not post_owner_id:
        reply_msg_id = reply_to.get("message_id")
        matched_post = find_post_by_channel_message(str(chat.get("id")), reply_msg_id)
        if matched_post:
            post_owner_id = matched_post.get("user_id")
            post_preview = matched_post.get("text") or ""
        else:
            post_owner_id = find_channel_owner(str(chat.get("id")))

    # Notify post owner if found and it's not the owner's own comment
    if post_owner_id and post_owner_id != sender_id:
        chat_uname = chat.get("username")
        msg_id = msg.get("message_id")
        comment_link = None
        if chat_uname:
            comment_link = f"https://t.me/{chat_uname}/{msg_id}"
        else:
            clean_id = str(chat.get("id")).replace("-100", "")
            comment_link = f"https://t.me/c/{clean_id}/{msg_id}"

        preview_snippet = (post_preview[:100] + "...") if len(post_preview) > 100 else (post_preview or "")

        notify_text = (
            "🔔 <b>Kanalingizdagi postga yangi izoh (kommentariya) yozildi!</b>\n\n"
            f"📢 <b>Kanal/Guruh:</b> {channel_title} {channel_identifier}\n"
            f"👤 <b>Kim yozdi:</b> <b>{sender_name}</b> {sender_uname}\n"
            f"💬 <b>Izoh matni:</b>\n<i>\"{comment_text}\"</i>\n"
        )
        if preview_snippet:
            notify_text += f"\n📝 <b>Post matni:</b> <i>{preview_snippet}</i>\n"

        markup = None
        if comment_link:
            markup = {
                "inline_keyboard": [
                    [{"text": "💬 Izohni ko'rish / Javob yozish", "url": comment_link}]
                ]
            }

        try:
            await send_message(str(post_owner_id), notify_text, reply_markup=markup)
            logger.info(f"✅ Izoh bildirishnomasi foydalanuvchi {post_owner_id} ga yuborildi.")
        except Exception as e:
            logger.error(f"Izoh bildirishnomasini yuborishda xatolik: {e}")

async def handle_callback_query(callback: Dict[str, Any]):
    cq_id = callback["id"]
    data = callback.get("data", "")
    from_user = callback.get("from", {})
    user_id = from_user.get("id")
    message = callback.get("message")

    if data.startswith("react:"):
        parts = data.split(":", 2)
        if len(parts) == 3:
            try:
                post_id = int(parts[1])
                emoji = parts[2]
                post = get_post(post_id)
                if post:
                    toggle_post_reaction(post_id, user_id, emoji)
                    chat_id = str(message["chat"]["id"])
                    msg_id = message["message_id"]
                    buttons_cfg = post.get("buttons_config", {})
                    await refresh_post_markup(post_id, chat_id, msg_id, buttons_cfg)
                    await answer_callback_query(cq_id, text=f"Ovozingiz {emoji} qabul qilindi!")
                    return
            except Exception as e:
                logger.error(f"Error handling reaction callback: {e}")

        await answer_callback_query(cq_id, text="Ovoz berildi!")
        return

    if data == "action_help":
        if message:
            await handle_help(message["chat"]["id"])
        await answer_callback_query(cq_id)
        return

    if data == "action_check_channel":
        msg = (
            "Kanalni tekshirish uchun:\n"
            "1. Pastdagi <b>'📢 O'z kanalimni tanlash'</b> tugmasini bosing yoki\n"
            "2. Kanalingiz username'ini (masalan: <code>@mening_kanalim</code>) botga yuboring."
        )
        if message:
            await send_message(str(message["chat"]["id"]), msg)
        await answer_callback_query(cq_id)
        return

    await answer_callback_query(cq_id)

async def handle_message(msg: Dict[str, Any]):
    # Check for comment replies first
    if "reply_to_message" in msg:
        await check_and_notify_comment(msg)

    # Check for native chat_shared event
    if "chat_shared" in msg:
        await handle_chat_shared(msg)
        return

    chat_id = msg["chat"]["id"]
    from_user = msg.get("from", {})
    user_id = from_user.get("id", chat_id)
    text = (msg.get("text") or "").strip()

    if text.startswith("/start"):
        username = from_user.get("first_name", "")
        await handle_start(chat_id, user_id, username)
        return

    if text.startswith("/help"):
        await handle_help(chat_id)
        return

    if text.startswith("/app"):
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🚀 Mini Appni ochish", "web_app": {"url": WEBAPP_URL}}]
            ]
        }
        await send_message(str(chat_id), "Mini Appni ochish uchun quyidagi tugmani bosing:", reply_markup=reply_markup)
        return

    # Check if text is a channel username or id
    if text.startswith("@") or text.startswith("-100"):
        res = await check_bot_channel_admin(text)
        if res.get("ok"):
            save_channel(user_id, text, title=text)
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "✨ Mini Appda post yaratish", "web_app": {"url": WEBAPP_URL}}]
                ]
            }
            await send_message(
                str(chat_id),
                f"✅ <b>Kanal muvaffaqiyatli ulandi va tekshirildi!</b>\n"
                f"Kanal: <code>{text}</code>\n"
                f"Bot administrator huquqlariga ega.\n\n"
                f"Endi bemalol post tayyorlashingiz mumkin!",
                reply_markup=reply_markup
            )
        else:
            await send_message(
                str(chat_id),
                f"❌ <b>Xatolik:</b> {res.get('description')}\n\n"
                f"Iltimos, botni <code>{text}</code> kanaliga administrator qilib qo'shing va qayta yuboring."
            )
        return

    # Fallback message
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 Mini Appni ochish", "web_app": {"url": WEBAPP_URL}}]
        ]
    }
    await send_message(
        str(chat_id),
        "Post yaratish yoki rejalashtirish uchun <b>Mini Appni oching</b> yoki pastdagi <b>'📢 O'z kanalimni tanlash'</b> tugmasini bosing.",
        reply_markup=reply_markup
    )

async def handle_my_chat_member(update: Dict[str, Any]):
    """Automatically records channel when bot is added as admin."""
    chat = update.get("chat", {})
    new_member = update.get("new_chat_member", {})
    from_user = update.get("from", {})
    status = new_member.get("status")
    
    if status == "administrator":
        channel_id = str(chat.get("id"))
        username = chat.get("username")
        title = chat.get("title", "")
        identifier = f"@{username}" if username else channel_id
        user_id = from_user.get("id", 0)
        
        save_channel(user_id, identifier, title=title)
        logger.info(f"Bot channelga admin qilindi: {identifier} ({title})")
        
        # Also notify user in private message if user_id is valid
        if user_id > 0:
            try:
                await send_message(
                    str(user_id),
                    f"🎉 <b>{title}</b> ({identifier}) kanalingizga bot administrator sifatida muvaffaqiyatli ulandi!\n"
                    f"Endi Mini App orqali ushbu kanalga to'g'ridan-to'g'ri postlar joylashingiz mumkin.",
                    reply_markup={"inline_keyboard": [[{"text": "📱 Mini Appni ochish", "web_app": {"url": WEBAPP_URL}}]]}
                )
            except Exception as e:
                pass

async def bot_polling_worker():
    """Long polling loop for Telegram Bot updates."""
    offset = 0
    logger.info("🤖 Telegram Bot Polling ishga tushdi...")

    try:
        await set_bot_commands()
        await set_menu_button(WEBAPP_URL)
        logger.info(f"Bot menyusi va WebApp URL o'rnatildi: {WEBAPP_URL}")
    except Exception as e:
        logger.error(f"Bot sozlashda xatolik: {e}")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                params = {
                    "offset": offset,
                    "timeout": 20,
                    "allowed_updates": [
                        "message",
                        "edited_message",
                        "channel_post",
                        "edited_channel_post",
                        "callback_query",
                        "my_chat_member",
                        "chat_member"
                    ]
                }
                async with session.post(f"{API_URL}/getUpdates", json=params, timeout=25) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            offset = update["update_id"] + 1

                            if "message" in update:
                                await handle_message(update["message"])
                            elif "callback_query" in update:
                                await handle_callback_query(update["callback_query"])
                            elif "my_chat_member" in update:
                                await handle_my_chat_member(update["my_chat_member"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                await asyncio.sleep(3)
