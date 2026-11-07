import asyncio
import logging
from datetime import datetime
from app.database import (
    get_due_scheduled_posts,
    get_due_recurring_templates,
    create_post,
    calculate_next_run,
    update_template_run_time
)
from app.publisher import publish_post

logger = logging.getLogger(__name__)

def format_template_text(text: str) -> str:
    """Replaces dynamic date/time variables in templates."""
    now = datetime.now()
    weekdays_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    months_uz = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
    
    res = text.replace("{sana}", now.strftime("%d.%m.%Y"))
    res = res.replace("{vaqt}", now.strftime("%H:%M"))
    res = res.replace("{kun}", weekdays_uz[now.weekday()])
    res = res.replace("{oy}", months_uz[now.month - 1])
    res = res.replace("{yil}", str(now.year))
    return res

async def process_recurring_templates(now_iso: str):
    """Processes recurring templates and publishes due posts."""
    due_templates = get_due_recurring_templates(now_iso)
    for tpl in due_templates:
        tpl_id = tpl["id"]
        logger.info(f"🔄 Avto-post shabloni ishga tushdi: #{tpl_id} ('{tpl['name']}') -> {tpl['target_channel']}")
        try:
            # 1. Format text with dynamic variables
            post_text = format_template_text(tpl["text"] or "")
            
            # 2. Create actual post record
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

            # 3. Publish immediately
            res = await publish_post(post_id)
            if res.get("ok"):
                logger.info(f"✅ Shablon #{tpl_id} asosida post #{post_id} muvaffaqiyatli chop etildi!")
            else:
                logger.error(f"❌ Shablon #{tpl_id} asosidagi post xatosi: {res.get('error')}")

            # 4. Schedule next run
            next_run_iso = calculate_next_run(tpl["interval_type"], tpl["interval_value"], tpl["daily_time"])
            update_template_run_time(tpl_id, now_iso, next_run_iso)
            logger.info(f"⏳ Shablon #{tpl_id} uchun keyingi yuborish vaqti: {next_run_iso}")

        except Exception as e:
            logger.error(f"❌ Xatolik avto-shablonda #{tpl_id}: {e}")

async def scheduled_posts_worker():
    """Background task checking every 15 seconds for scheduled posts and recurring templates."""
    logger.info("📅 Rejalashtirilgan va Avto-postlar tekshiruvi (Scheduler) faol.")
    while True:
        try:
            now_iso = datetime.now().isoformat()
            
            # 1. Check one-time scheduled posts
            due_posts = get_due_scheduled_posts(now_iso)
            for post in due_posts:
                post_id = post["id"]
                logger.info(f"🚀 Rejalashtirilgan post chop etilmoqda: #{post_id} -> {post['target_channel']}")
                try:
                    result = await publish_post(post_id)
                    if result.get("ok"):
                        logger.info(f"✅ Post #{post_id} muvaffaqiyatli chop etildi!")
                    else:
                        logger.error(f"❌ Post #{post_id} chop etilmadi: {result.get('error')}")
                except Exception as e:
                    logger.error(f"❌ Scheduler post #{post_id} xatosi: {e}")

            # 2. Check recurring templates
            await process_recurring_templates(now_iso)

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")

        await asyncio.sleep(15)
