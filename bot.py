import telebot
import sqlite3
import random
import string
import re
from datetime import datetime

# ---------------- CONFIG ----------------
TOKEN =  "8808428509:AAFfY4kU_ME-QOxcVDmwMZz7Oph6lJcok1A"
OWNER_ID = 8725158233

bot = telebot.TeleBot(TOKEN)

# ---------------- DB ----------------
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keys (
    key TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0,
    used_by INTEGER,
    ip TEXT,
    created_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY
)
""")

db.commit()

admins = [OWNER_ID]
waiting_key = {}
waiting_ip = {}

# ---------------- KEY GEN ----------------
def gen_key():
    chars = string.ascii_uppercase + string.digits
    return (
        f"SinX-"
        f"{''.join(random.choice(chars) for _ in range(5))}-"
        f"{''.join(random.choice(chars) for _ in range(5))}-"
        f"{''.join(random.choice(chars) for _ in range(5))}"
    )

# ---------------- IP CHECK ----------------
def valid_ip(ip):
    return bool(
        re.match(
            r"^(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})"
            r"(?:\.(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}$",
            ip,
        )
    )

# ---------------- ADMIN ----------------
def is_admin(uid):
    return uid in admins

# ---------------- MENU ----------------
def menu():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔑 Generate Key", "📋 All Keys")
    kb.row("📊 Statistics")
    kb.row("👤 My Profile")
    return kb

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id

    if is_admin(uid):
        bot.send_message(
            m.chat.id,
            "👑 Admin Panel",
            reply_markup=menu()
        )
    else:
        waiting_key[uid] = True

        bot.send_message(
            m.chat.id,
            """👋 Welcome to SinX Proxy
━━━━━━━━━━━━━━━━━━━━
Send your key to activate access.

Example:
SinX-XXXXX-XXXXX-XXXXX"""
        )

# ---------------- MAIN ----------------
@bot.message_handler(func=lambda m: True)
def handle(m):

    uid = m.from_user.id
    text = m.text.strip()

    # KEY CHECK
    if waiting_key.get(uid):

        cur.execute(
            "SELECT * FROM keys WHERE key=?",
            (text,)
        )

        key = cur.fetchone()

        if not key:
            bot.send_message(
                m.chat.id,
                "❌ Invalid Key"
            )
            return

        if key[1] == 1:
            bot.send_message(
                m.chat.id,
                "❌ Key already used"
            )
            return

        waiting_key.pop(uid)
        waiting_ip[uid] = text

        bot.send_message(
            m.chat.id,
            f"""✅ Key Verified!

🔑 {text}

Send your IP:"""
        )

        return

    # IP FLOW
    if uid in waiting_ip:

        if not valid_ip(text):

            bot.send_message(
                m.chat.id,
                "⚠️ Invalid IP"
            )

            return

        key = waiting_ip[uid]

        cur.execute("""
        UPDATE keys
        SET used=1,
            used_by=?,
            ip=?,
            created_at=?
        WHERE key=?
        """, (
            uid,
            text,
            str(datetime.utcnow()),
            key
        ))

        db.commit()

        waiting_ip.pop(uid)

        bot.send_message(
            m.chat.id,
            f"""🎉 Activated

IP: {text}
Duration: 1 Day"""
        )

        return

    if not is_admin(uid):
        return

    # GENERATE
    if text == "🔑 Generate Key":

        k = gen_key()

        cur.execute(
            "INSERT INTO keys(key,created_at) VALUES(?,?)",
            (
                k,
                str(datetime.utcnow())
            )
        )

        db.commit()

        bot.send_message(
            m.chat.id,
            f"🔑\n{k}"
        )

        return

    # LIST
    if text == "📋 All Keys":

        cur.execute(
            "SELECT key,used FROM keys"
        )

        rows = cur.fetchall()

        msg = "📋 Keys\n\n"

        for k, u in rows:
            msg += f"{k} | {'USED' if u else 'FREE'}\n"

        bot.send_message(
            m.chat.id,
            msg
        )

        return

    # STATS
    if text == "📊 Statistics":

        cur.execute(
            "SELECT COUNT(*) FROM keys"
        )

        t = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM keys WHERE used=1"
        )

        u = cur.fetchone()[0]

        bot.send_message(
            m.chat.id,
            f"""📊 Statistics

Total: {t}
Used: {u}"""
        )

        return

    # PROFILE
    if text == "👤 My Profile":

        bot.send_message(
            m.chat.id,
            f"""ID: {uid}
Name: {m.from_user.first_name}"""
        )

print("Bot Running...")

bot.infinity_polling()