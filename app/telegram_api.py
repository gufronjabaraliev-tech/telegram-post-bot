import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
from app.config import BOT_TOKEN

logger = logging.getLogger(__name__)

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def call_api(method: str, data: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    url = f"{API_URL}/{method}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data or {}, timeout=timeout) as response:
                result = await response.json()
                return result
        except Exception as e:
            logger.error(f"Telegram API call error ({method}): {e}")
            return {"ok": False, "description": str(e)}

async def get_me() -> Dict[str, Any]:
    return await call_api("getMe")

async def get_chat(chat_id: str) -> Dict[str, Any]:
    return await call_api("getChat", {"chat_id": chat_id})

async def check_bot_channel_admin(chat_id: str) -> Dict[str, Any]:
    """Check if bot has permissions to post messages in the given channel/chat."""
    bot_info = await get_me()
    if not bot_info.get("ok"):
        return {"ok": False, "description": "Bot tokeni orqali ulanib bo'lmadi"}
    
    bot_id = bot_info["result"]["id"]
    
    # Check chat member status
    url = f"{API_URL}/getChatMember"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"chat_id": chat_id, "user_id": bot_id}) as response:
                res = await response.json()
                if not res.get("ok"):
                    return {"ok": False, "description": f"Kanal topilmadi yoki bot kanalga a'zo emas ({res.get('description')})"}
                
                status = res["result"]["status"]
                if status not in ("administrator", "creator"):
                    return {"ok": False, "description": "Bot kanalda ADMIN emas! Iltimos, avval botni kanalga administrator qilib qo'shing."}
                
                can_post = res["result"].get("can_post_messages", True)
                if not can_post:
                    return {"ok": False, "description": "Bot admin, lekin 'Xabarlarni joylash' (can_post_messages) huquqi berilmagan."}
                
                return {"ok": True, "result": res["result"]}
        except Exception as e:
            return {"ok": False, "description": str(e)}

async def set_menu_button(web_app_url: str):
    """Sets Telegram Bot Menu button to open the Web App."""
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "📱 Mini App",
            "web_app": {"url": web_app_url}
        }
    }
    return await call_api("setChatMenuButton", payload)

async def set_bot_commands():
    payload = {
        "commands": [
            {"command": "start", "description": "Botni ishga tushirish va Mini Appni ochish"},
            {"command": "app", "description": "Post yaratuvchi Mini Appni ochish"},
            {"command": "help", "description": "Foydalanish bo'yicha yo'riqnoma"}
        ]
    }
    return await call_api("setMyCommands", payload)

async def send_message(
    chat_id: str,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
    parse_mode: str = "HTML",
    disable_notification: bool = False
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
        "disable_web_page_preview": False
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await call_api("sendMessage", payload)

async def send_single_photo(
    chat_id: str,
    photo_path: Path,
    caption: str = "",
    reply_markup: Optional[Dict[str, Any]] = None,
    parse_mode: str = "HTML",
    disable_notification: bool = False
) -> Dict[str, Any]:
    url = f"{API_URL}/sendPhoto"
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("caption", caption)
        data.add_field("parse_mode", parse_mode)
        data.add_field("disable_notification", "true" if disable_notification else "false")
        
        if reply_markup:
            data.add_field("reply_markup", json.dumps(reply_markup))
            
        with open(photo_path, "rb") as f:
            data.add_field(
                "photo",
                f.read(),
                filename=photo_path.name,
                content_type="image/jpeg"
            )
        
        async with session.post(url, data=data) as response:
            return await response.json()

async def send_album_media_group(
    chat_id: str,
    photo_paths: List[Path],
    caption: str = "",
    parse_mode: str = "HTML",
    disable_notification: bool = False
) -> Dict[str, Any]:
    """Sends 2-10 photos as a Telegram media group (album)."""
    url = f"{API_URL}/sendMediaGroup"
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("disable_notification", "true" if disable_notification else "false")
        
        media_list = []
        file_handles = []
        try:
            for idx, p in enumerate(photo_paths):
                attach_name = f"photo_{idx}"
                item: Dict[str, Any] = {
                    "type": "photo",
                    "media": f"attach://{attach_name}"
                }
                # Attach caption only to the first media item per Telegram requirements
                if idx == 0 and caption:
                    item["caption"] = caption
                    item["parse_mode"] = parse_mode
                media_list.append(item)
                
                with open(p, "rb") as f:
                    content = f.read()
                data.add_field(attach_name, content, filename=p.name, content_type="image/jpeg")

            data.add_field("media", json.dumps(media_list))
            
            async with session.post(url, data=data) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"sendMediaGroup error: {e}")
            return {"ok": False, "description": str(e)}

async def edit_reply_markup(chat_id: str, message_id: int, reply_markup: Dict[str, Any]) -> Dict[str, Any]:
    return await call_api("editMessageReplyMarkup", {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": reply_markup
    })

async def pin_message(chat_id: str, message_id: int, disable_notification: bool = False) -> Dict[str, Any]:
    return await call_api("pinChatMessage", {
        "chat_id": chat_id,
        "message_id": message_id,
        "disable_notification": disable_notification
    })

async def answer_callback_query(callback_query_id: str, text: Optional[str] = None, show_alert: bool = False):
    payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        payload["text"] = text
    return await call_api("answerCallbackQuery", payload)
