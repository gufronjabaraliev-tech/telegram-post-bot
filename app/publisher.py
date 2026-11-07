import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import UPLOAD_DIR
from app.database import (
    get_post,
    update_post_status,
    get_post_reaction_counts
)
from app.telegram_api import (
    send_single_photo,
    send_album_media_group,
    send_message,
    pin_message,
    edit_reply_markup
)

logger = logging.getLogger(__name__)

def build_inline_keyboard(post_id: int, buttons_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Builds the inline keyboard array based on:
    - Reactions (with dynamic counts)
    - Share button
    - Comments button
    - Custom URL buttons
    """
    inline_keyboard = []
    
    # 1. Reaction buttons row
    reactions = buttons_config.get("reactions", [])
    if reactions:
        counts = get_post_reaction_counts(post_id)
        reaction_row = []
        for r in reactions:
            emoji = r.get("emoji") if isinstance(r, dict) else r
            cnt = counts.get(emoji, 0)
            btn_text = f"{emoji} {cnt}" if cnt > 0 else f"{emoji}"
            reaction_row.append({
                "text": btn_text,
                "callback_data": f"react:{post_id}:{emoji}"
            })
        if reaction_row:
            inline_keyboard.append(reaction_row)

    # 2. Share & Comments row
    actions_row = []
    
    # Share button
    if buttons_config.get("share", {}).get("enabled"):
        share_cfg = buttons_config["share"]
        share_title = share_cfg.get("text", "↗️ Ulashish")
        share_url = share_cfg.get("url", "")
        share_text = share_cfg.get("share_text", "")
        
        # Build tg share link
        encoded_url = urllib.parse.quote(share_url)
        encoded_text = urllib.parse.quote(share_text)
        tg_share = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"
        
        actions_row.append({
            "text": share_title,
            "url": tg_share
        })
        
    # Comments button
    if buttons_config.get("comments", {}).get("enabled"):
        comments_cfg = buttons_config["comments"]
        comment_title = comments_cfg.get("text", "💬 Izohlar")
        comment_url = comments_cfg.get("url", "")
        if comment_url:
            actions_row.append({
                "text": comment_title,
                "url": comment_url
            })

    if actions_row:
        inline_keyboard.append(actions_row)

    # 3. Custom URL buttons
    custom_buttons = buttons_config.get("custom_buttons", [])
    for btn in custom_buttons:
        text = btn.get("text")
        url = btn.get("url")
        if text and url:
            inline_keyboard.append([{
                "text": text,
                "url": url
            }])

    if not inline_keyboard:
        return None
    
    return {"inline_keyboard": inline_keyboard}


async def refresh_post_markup(post_id: int, channel_id: str, message_id: int, buttons_config: Dict[str, Any]):
    """Refreshes the inline keyboard (reactions count) on an existing message."""
    markup = build_inline_keyboard(post_id, buttons_config)
    if markup:
        await edit_reply_markup(channel_id, message_id, markup)


async def publish_post(post_id: int) -> Dict[str, Any]:
    """
    Publishes a post (single photo, album with 2-10 photos, or text).
    Attaches interactive buttons (reactions, share, comments, custom links).
    """
    post = get_post(post_id)
    if not post:
        return {"ok": False, "error": f"Post #{post_id} topilmadi"}

    channel_id = post["target_channel"]
    text = post["text"] or ""
    image_filenames = post["images"] or []
    buttons_config = post["buttons_config"] or {}
    pin_post_flag = bool(post.get("pin_post"))
    silent_flag = bool(post.get("silent"))

    photo_paths = []
    for fn in image_filenames:
        p = UPLOAD_DIR / fn
        if p.exists():
            photo_paths.append(p)

    sent_message_ids = []
    interaction_message_id = None

    try:
        if len(photo_paths) == 0:
            # Text-only post
            markup = build_inline_keyboard(post_id, buttons_config)
            res = await send_message(
                chat_id=channel_id,
                text=text,
                reply_markup=markup,
                parse_mode="HTML",
                disable_notification=silent_flag
            )
            if not res.get("ok"):
                err = res.get("description", "Xatolik yuz berdi")
                update_post_status(post_id, "failed", error_message=err)
                return {"ok": False, "error": err}
            
            msg_id = res["result"]["message_id"]
            sent_message_ids.append(msg_id)
            interaction_message_id = msg_id

        elif len(photo_paths) == 1:
            # Single photo post -> Telegram natively attaches reply_markup to sendPhoto!
            markup = build_inline_keyboard(post_id, buttons_config)
            res = await send_single_photo(
                chat_id=channel_id,
                photo_path=photo_paths[0],
                caption=text,
                reply_markup=markup,
                parse_mode="HTML",
                disable_notification=silent_flag
            )
            if not res.get("ok"):
                err = res.get("description", "Rasmni yuklashda xatolik")
                update_post_status(post_id, "failed", error_message=err)
                return {"ok": False, "error": err}
            
            msg_id = res["result"]["message_id"]
            sent_message_ids.append(msg_id)
            interaction_message_id = msg_id

        else:
            # 2 to 10 photos -> sendMediaGroup album
            res = await send_album_media_group(
                chat_id=channel_id,
                photo_paths=photo_paths,
                caption=text,
                parse_mode="HTML",
                disable_notification=silent_flag
            )
            if not res.get("ok"):
                err = res.get("description", "Media guruhini yuklashda xatolik")
                update_post_status(post_id, "failed", error_message=err)
                return {"ok": False, "error": err}

            for m in res.get("result", []):
                sent_message_ids.append(m["message_id"])

            # Because Telegram API doesn't support reply_markup on sendMediaGroup albums,
            # if buttons/reactions/comments are configured, we send an elegant interaction bar below the album!
            markup = build_inline_keyboard(post_id, buttons_config)
            if markup:
                bar_text = buttons_config.get("bar_text", "👇 <b>Fikr bildiring va ulashing:</b>")
                res_bar = await send_message(
                    chat_id=channel_id,
                    text=bar_text,
                    reply_markup=markup,
                    parse_mode="HTML",
                    disable_notification=silent_flag
                )
                if res_bar.get("ok"):
                    interaction_message_id = res_bar["result"]["message_id"]
                    sent_message_ids.append(interaction_message_id)

        # Pin post if requested
        if pin_post_flag and sent_message_ids:
            try:
                await pin_message(channel_id, sent_message_ids[0], disable_notification=silent_flag)
            except Exception as e:
                logger.warning(f"Could not pin message: {e}")

        now_iso = datetime.now().isoformat()
        update_post_status(
            post_id=post_id,
            status="published",
            published_at=now_iso,
            sent_message_ids=sent_message_ids,
            interaction_message_id=interaction_message_id
        )

        return {
            "ok": True,
            "post_id": post_id,
            "sent_message_ids": sent_message_ids,
            "published_at": now_iso
        }

    except Exception as e:
        logger.error(f"Error publishing post {post_id}: {e}")
        update_post_status(post_id, "failed", error_message=str(e))
        return {"ok": False, "error": str(e)}
