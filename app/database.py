import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # User saved channels
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        channel_id TEXT NOT NULL,
        title TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, channel_id)
    )
    """)

    # Posts (draft, scheduled, published)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        target_channel TEXT NOT NULL,
        text TEXT,
        images TEXT,
        buttons_config TEXT,
        status TEXT DEFAULT 'draft',
        scheduled_at TEXT NULL,
        published_at TEXT NULL,
        sent_message_ids TEXT NULL,
        interaction_message_id INTEGER NULL,
        pin_post INTEGER DEFAULT 0,
        silent INTEGER DEFAULT 0,
        error_message TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Reactions recorded for inline buttons
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS post_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        emoji TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(post_id, user_id, emoji)
    )
    """)

    # Post templates & Recurring auto-posters
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        target_channel TEXT NOT NULL,
        text TEXT,
        images TEXT,
        buttons_config TEXT,
        is_recurring INTEGER DEFAULT 0,
        interval_type TEXT DEFAULT 'daily',
        interval_value INTEGER DEFAULT 1,
        daily_time TEXT NULL,
        weekdays TEXT NULL,
        pin_post INTEGER DEFAULT 0,
        silent INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        last_run_at TEXT NULL,
        next_run_at TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

# Channel operations
def save_channel(user_id: int, channel_id: str, title: str = ""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO channels (user_id, channel_id, title)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id, channel_id) DO UPDATE SET title=excluded.title
    """, (user_id, channel_id.strip(), title.strip()))
    conn.commit()
    conn.close()

def get_user_channels(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels WHERE user_id = ? ORDER BY added_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_user_channel(user_id: int, channel_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
    conn.commit()
    conn.close()

def find_channel_owner(channel_identifier: str) -> Optional[int]:
    """Finds the user_id who added this channel/chat."""
    conn = get_db()
    cursor = conn.cursor()
    clean_id = str(channel_identifier).strip().replace("@", "")
    cursor.execute("""
    SELECT user_id FROM channels 
    WHERE channel_id = ? OR channel_id = ? OR channel_id LIKE ? 
    ORDER BY added_at DESC LIMIT 1
    """, (channel_identifier, f"@{clean_id}", f"%{clean_id}%"))
    row = cursor.fetchone()
    conn.close()
    return row["user_id"] if row else None

def find_post_by_channel_message(channel_identifier: str, message_id: int) -> Optional[Dict[str, Any]]:
    """Finds a published post by its sent message_id in the channel."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM posts 
    WHERE status = 'published' AND sent_message_ids LIKE ?
    ORDER BY id DESC LIMIT 5
    """, (f"%{message_id}%",))
    rows = cursor.fetchall()
    conn.close()
    for r in rows:
        d = dict(r)
        msg_ids = json.loads(d["sent_message_ids"] or "[]")
        if message_id in msg_ids:
            d["images"] = json.loads(d["images"] or "[]")
            d["buttons_config"] = json.loads(d["buttons_config"] or "{}")
            d["sent_message_ids"] = msg_ids
            return d
    return None

# Post operations
def create_post(
    user_id: int,
    target_channel: str,
    text: str,
    images: List[str],
    buttons_config: Dict[str, Any],
    status: str = "draft",
    scheduled_at: Optional[str] = None,
    pin_post: bool = False,
    silent: bool = False
) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO posts (user_id, target_channel, text, images, buttons_config, status, scheduled_at, pin_post, silent)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        target_channel.strip(),
        text,
        json.dumps(images),
        json.dumps(buttons_config),
        status,
        scheduled_at,
        1 if pin_post else 0,
        1 if silent else 0
    ))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id

def get_post(post_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["images"] = json.loads(data["images"] or "[]")
    data["buttons_config"] = json.loads(data["buttons_config"] or "{}")
    data["sent_message_ids"] = json.loads(data["sent_message_ids"] or "[]")
    return data

def get_user_posts(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM posts 
    WHERE user_id = ? 
    ORDER BY created_at DESC 
    LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["images"] = json.loads(d["images"] or "[]")
        d["buttons_config"] = json.loads(d["buttons_config"] or "{}")
        d["sent_message_ids"] = json.loads(d["sent_message_ids"] or "[]")
        result.append(d)
    return result

def get_due_scheduled_posts(now_iso: str) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM posts 
    WHERE status = 'scheduled' AND scheduled_at <= ? 
    ORDER BY scheduled_at ASC
    """, (now_iso,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["images"] = json.loads(d["images"] or "[]")
        d["buttons_config"] = json.loads(d["buttons_config"] or "{}")
        d["sent_message_ids"] = json.loads(d["sent_message_ids"] or "[]")
        result.append(d)
    return result

def update_post_status(
    post_id: int,
    status: str,
    published_at: Optional[str] = None,
    sent_message_ids: Optional[List[int]] = None,
    interaction_message_id: Optional[int] = None,
    error_message: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()
    updates = ["status = ?"]
    params = [status]
    
    if published_at is not None:
        updates.append("published_at = ?")
        params.append(published_at)
    if sent_message_ids is not None:
        updates.append("sent_message_ids = ?")
        params.append(json.dumps(sent_message_ids))
    if interaction_message_id is not None:
        updates.append("interaction_message_id = ?")
        params.append(interaction_message_id)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
        
    params.append(post_id)
    query = f"UPDATE posts SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def delete_post(post_id: int, user_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

# Reaction operations
def toggle_post_reaction(post_id: int, user_id: int, emoji: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM post_reactions WHERE post_id = ? AND user_id = ? AND emoji = ?", (post_id, user_id, emoji))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM post_reactions WHERE id = ?", (row["id"],))
        added = False
    else:
        cursor.execute("INSERT INTO post_reactions (post_id, user_id, emoji) VALUES (?, ?, ?)", (post_id, user_id, emoji))
        added = True
    conn.commit()
    conn.close()
    return added

def get_post_reaction_counts(post_id: int) -> Dict[str, int]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT emoji, COUNT(*) as cnt 
    FROM post_reactions 
    WHERE post_id = ? 
    GROUP BY emoji
    """, (post_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row["emoji"]: row["cnt"] for row in rows}

# Template and Recurring operations
def calculate_next_run(interval_type: str, interval_value: int, daily_time: Optional[str] = None) -> str:
    now = datetime.now()
    if interval_type == "interval_minutes":
        next_time = now + timedelta(minutes=max(1, interval_value))
    elif interval_type == "interval_hours":
        next_time = now + timedelta(hours=max(1, interval_value))
    elif interval_type == "daily":
        target_h, target_m = 9, 0
        if daily_time and ":" in daily_time:
            try:
                parts = daily_time.split(":")
                target_h, target_m = int(parts[0]), int(parts[1])
            except:
                pass
        next_time = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        if next_time <= now:
            next_time += timedelta(days=1)
    else:
        next_time = now + timedelta(hours=1)
    return next_time.isoformat()

def create_template(
    user_id: int,
    name: str,
    target_channel: str,
    text: str,
    images: List[str],
    buttons_config: Dict[str, Any],
    is_recurring: bool = False,
    interval_type: str = "daily",
    interval_value: int = 1,
    daily_time: Optional[str] = None,
    weekdays: Optional[List[int]] = None,
    pin_post: bool = False,
    silent: bool = False,
    is_active: bool = True
) -> int:
    conn = get_db()
    cursor = conn.cursor()
    
    next_run = None
    if is_recurring and is_active:
        next_run = calculate_next_run(interval_type, interval_value, daily_time)

    cursor.execute("""
    INSERT INTO templates (
        user_id, name, target_channel, text, images, buttons_config,
        is_recurring, interval_type, interval_value, daily_time, weekdays,
        pin_post, silent, is_active, next_run_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        name.strip(),
        target_channel.strip(),
        text,
        json.dumps(images),
        json.dumps(buttons_config),
        1 if is_recurring else 0,
        interval_type,
        interval_value,
        daily_time,
        json.dumps(weekdays or []),
        1 if pin_post else 0,
        1 if silent else 0,
        1 if is_active else 0,
        next_run
    ))
    tpl_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tpl_id

def get_user_templates(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["images"] = json.loads(d["images"] or "[]")
        d["buttons_config"] = json.loads(d["buttons_config"] or "{}")
        d["weekdays"] = json.loads(d["weekdays"] or "[]")
        result.append(d)
    return result

def get_template(template_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["images"] = json.loads(d["images"] or "[]")
    d["buttons_config"] = json.loads(d["buttons_config"] or "{}")
    d["weekdays"] = json.loads(d["weekdays"] or "[]")
    return d

def update_template_status(template_id: int, is_active: bool):
    conn = get_db()
    cursor = conn.cursor()
    tpl = get_template(template_id)
    if not tpl:
        conn.close()
        return
    next_run = None
    if is_active and tpl["is_recurring"]:
        next_run = calculate_next_run(tpl["interval_type"], tpl["interval_value"], tpl["daily_time"])
    cursor.execute("UPDATE templates SET is_active = ?, next_run_at = ? WHERE id = ?", (1 if is_active else 0, next_run, template_id))
    conn.commit()
    conn.close()

def update_template_run_time(template_id: int, last_run_iso: str, next_run_iso: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE templates SET last_run_at = ?, next_run_at = ? WHERE id = ?", (last_run_iso, next_run_iso, template_id))
    conn.commit()
    conn.close()

def delete_template(template_id: int, user_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM templates WHERE id = ? AND user_id = ?", (template_id, user_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def get_due_recurring_templates(now_iso: str) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM templates 
    WHERE is_recurring = 1 AND is_active = 1 AND next_run_at IS NOT NULL AND next_run_at <= ? 
    ORDER BY next_run_at ASC
    """, (now_iso,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["images"] = json.loads(d["images"] or "[]")
        d["buttons_config"] = json.loads(d["buttons_config"] or "{}")
        d["weekdays"] = json.loads(d["weekdays"] or "[]")
        result.append(d)
    return result
