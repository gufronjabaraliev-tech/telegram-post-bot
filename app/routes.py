import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Header
from pydantic import BaseModel

from app.config import UPLOAD_DIR
from app.database import (
    save_channel,
    get_user_channels,
    delete_user_channel,
    create_post,
    get_post,
    get_user_posts,
    delete_post,
    update_post_status,
    create_template,
    get_user_templates,
    get_template,
    update_template_status,
    update_template_run_time,
    delete_template,
    calculate_next_run
)
from app.publisher import publish_post
from app.telegram_api import check_bot_channel_admin, get_me
from app.security import verify_telegram_init_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_SIZE = 15 * 1024 * 1024 # 15MB

class ChannelRequest(BaseModel):
    user_id: int
    channel_id: str
    title: Optional[str] = ""

class CreatePostRequest(BaseModel):
    user_id: int
    target_channel: str
    text: str
    images: List[str] = []
    buttons_config: dict = {}
    scheduled_at: Optional[str] = None
    pin_post: bool = False
    silent: bool = False
    send_now: bool = False

class TemplateRequest(BaseModel):
    user_id: int
    name: str
    target_channel: str
    text: str
    images: List[str] = []
    buttons_config: dict = {}
    is_recurring: bool = False
    interval_type: str = "daily"
    interval_value: int = 1
    daily_time: Optional[str] = "09:00"
    weekdays: List[int] = []
    pin_post: bool = False
    silent: bool = False
    is_active: bool = True

def resolve_user_id(explicit_user_id: int, init_data_header: Optional[str] = None) -> int:
    """Verifies HMAC signature if initData header is passed, else validates user_id."""
    if init_data_header:
        valid, user_info = verify_telegram_init_data(init_data_header)
        if valid and user_info and "id" in user_info:
            return user_info["id"]
    return explicit_user_id

@router.get("/bot-info")
async def bot_info():
    me = await get_me()
    return me

@router.post("/verify-channel")
async def verify_channel(req: ChannelRequest, x_telegram_init_data: Optional[str] = Header(None)):
    user_id = resolve_user_id(req.user_id, x_telegram_init_data)
    cid = req.channel_id.strip()
    res = await check_bot_channel_admin(cid)
    if res.get("ok"):
        save_channel(user_id, cid, req.title or cid)
    return res

@router.get("/channels")
async def get_channels(user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    channels = get_user_channels(uid)
    return {"ok": True, "channels": channels}

@router.post("/channels")
async def add_channel(req: ChannelRequest, x_telegram_init_data: Optional[str] = Header(None)):
    user_id = resolve_user_id(req.user_id, x_telegram_init_data)
    cid = req.channel_id.strip()
    check = await check_bot_channel_admin(cid)
    if not check.get("ok"):
        return {"ok": False, "error": check.get("description", "Bot bu kanalda admin emas")}
    save_channel(user_id, cid, req.title or cid)
    return {"ok": True, "message": "Kanal saqlandi"}

@router.delete("/channels")
async def remove_channel(user_id: int = Query(...), channel_id: str = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    delete_user_channel(uid, channel_id)
    return {"ok": True}

@router.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maksimal 10 ta rasm yuklash mumkin")
    
    saved_files = []
    for f in files:
        ext = Path(f.filename or "img.jpg").suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Faqat rasmlar yuklanishi mumkin ({ext} qo'llab-quvvatlanmaydi)")

        content = await f.read()
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="Rasm hajmi 15MB dan oshmasligi kerak")

        unique_name = f"{uuid.uuid4().hex}{ext}"
        destination = UPLOAD_DIR / unique_name
        with open(destination, "wb") as buffer:
            buffer.write(content)

        saved_files.append({
            "filename": unique_name,
            "original_name": Path(f.filename).name,
            "url": f"/uploads/{unique_name}"
        })
    return {"ok": True, "files": saved_files}

@router.post("/posts/create")
async def handle_create_post(req: CreatePostRequest, x_telegram_init_data: Optional[str] = Header(None)):
    user_id = resolve_user_id(req.user_id, x_telegram_init_data)
    if len(req.images) > 10:
        raise HTTPException(status_code=400, detail="10 tadan ortiq rasm yuklab bo'lmaydi")

    status = "scheduled" if (req.scheduled_at and not req.send_now) else "draft"
    
    post_id = create_post(
        user_id=user_id,
        target_channel=req.target_channel,
        text=req.text,
        images=req.images,
        buttons_config=req.buttons_config,
        status=status,
        scheduled_at=req.scheduled_at,
        pin_post=req.pin_post,
        silent=req.silent
    )

    if req.send_now or not req.scheduled_at:
        publish_res = await publish_post(post_id)
        if not publish_res.get("ok"):
            return {
                "ok": False,
                "post_id": post_id,
                "error": publish_res.get("error", "Kanalga yuborishda xatolik yuz berdi")
            }
        return {
            "ok": True,
            "post_id": post_id,
            "status": "published",
            "message": "Post muvaffaqiyatli kanalga joylandi!"
        }
    else:
        return {
            "ok": True,
            "post_id": post_id,
            "status": "scheduled",
            "message": f"Post {req.scheduled_at} vaqtiga rejalashtirildi!"
        }

@router.get("/posts")
async def list_user_posts(user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    posts = get_user_posts(uid)
    return {"ok": True, "posts": posts}

@router.post("/posts/{post_id}/send-now")
async def post_send_now(post_id: int, user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    post = get_post(post_id)
    if not post or post["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Post topilmadi")
    res = await publish_post(post_id)
    return res

@router.delete("/posts/{post_id}")
async def post_delete(post_id: int, user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    ok = delete_post(post_id, uid)
    return {"ok": ok}

# Template Routes
@router.get("/templates")
async def list_templates(user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    tpls = get_user_templates(uid)
    return {"ok": True, "templates": tpls}

@router.post("/templates")
async def save_new_template(req: TemplateRequest, x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(req.user_id, x_telegram_init_data)
    tpl_id = create_template(
        user_id=uid,
        name=req.name,
        target_channel=req.target_channel,
        text=req.text,
        images=req.images,
        buttons_config=req.buttons_config,
        is_recurring=req.is_recurring,
        interval_type=req.interval_type,
        interval_value=req.interval_value,
        daily_time=req.daily_time,
        weekdays=req.weekdays,
        pin_post=req.pin_post,
        silent=req.silent,
        is_active=req.is_active
    )
    return {"ok": True, "template_id": tpl_id, "message": "Shablon muvaffaqiyatli saqlandi"}

@router.get("/templates/{tpl_id}")
async def get_single_template(tpl_id: int):
    tpl = get_template(tpl_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Shablon topilmadi")
    return {"ok": True, "template": tpl}

@router.post("/templates/{tpl_id}/toggle")
async def toggle_tpl_status(tpl_id: int, is_active: bool = Query(...)):
    update_template_status(tpl_id, is_active)
    return {"ok": True}

@router.post("/templates/{tpl_id}/run-now")
async def trigger_template_now(tpl_id: int, user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    tpl = get_template(tpl_id)
    if not tpl or tpl["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Shablon topilmadi")
    
    from app.scheduler import format_template_text
    post_text = format_template_text(tpl["text"] or "")
    
    post_id = create_post(
        user_id=tpl["user_id"],
        target_channel=tpl["target_channel"],
        text=post_text,
        images=tpl["images"] or [],
        buttons_config=tpl["buttons_config"] or {},
        status="draft",
        pin_post=bool(tpl.get("pin_post")),
        silent=bool(tpl.get("silent"))
    )
    res = await publish_post(post_id)
    if res.get("ok"):
        now_iso = datetime.now().isoformat()
        next_run_iso = calculate_next_run(tpl["interval_type"], tpl["interval_value"], tpl["daily_time"])
        update_template_run_time(tpl_id, now_iso, next_run_iso)
    return res

@router.delete("/templates/{tpl_id}")
async def remove_template(tpl_id: int, user_id: int = Query(...), x_telegram_init_data: Optional[str] = Header(None)):
    uid = resolve_user_id(user_id, x_telegram_init_data)
    ok = delete_template(tpl_id, uid)
    return {"ok": ok}
