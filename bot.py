import os
import telebot
import sqlite3
import random
import string
import re
from datetime import datetime

# ---------------- TOKEN ----------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN missing in environment variables")

bot = telebot.TeleBot(TOKEN)

OWNER_ID = 8725158233

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

# ---------------- LOAD ADMINS FROM DB ----------------
def load_admins():
    cur.execute("SELECT user_id FROM admins")
    rows = cur.fetchall()
    return [r[0] for r in rows]

admins = load_admins()

if OWNER_ID not in admins:
    cur.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (OWNER_ID,))
    db.commit()
    admins = load_admins()

# ---------------- STATE ----------------
waiting_key = {}
waiting_ip = {}

# ---------------- KEY GEN ----------------
def gen_key():
    chars = string.ascii_uppercase + string.digits
    return f"SinX-{''.join(random.choice(chars) for _ in range(5))}-{''.join(random.choice(chars) for _ in range(5))}-{''.join(random.choice(chars) for _ in range(5))}"

# ---------------- IP CHECK ----------------
def valid_ip(ip):
    return bool(re.match(r"^(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})(?:\.(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}$", ip))

# ---------------- ADMIN CHECK ----------------
def is_admin(uid):
    return uid in admins

# ---------------- MENU ----------------
def menu():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔑 Generate Key", "📋 All Keys")
    kb.row("📊 Statistics", "👤 My Profile")
    return kb

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id

    if is_admin(uid):
        bot.send_message(m.chat.id, "👑 Admin Panel", reply_markup=menu())
    else:
        waiting_key[uid] = True
        bot.send_message(m.chat.id,
        "👋 Welcome\nSend your key to continue:\n\nExample:\nSinX-XXXXX-XXXXX-XXXXX")

# ---------------- HANDLER ----------------
@bot.message_handler(func=lambda m: True)
def handle(m):

    uid = m.from_user.id
    text = m.text.strip()

    # ---------- USER KEY ----------
    if waiting_key.get(uid):

        cur.execute("SELECT * FROM keys WHERE key=?", (text,))
        key = cur.fetchone()

        if not key:
            bot.send_message(m.chat.id, "❌ Invalid Key")
            return

        if key[1] == 1:
            bot.send_message(m.chat.id, "❌ Key already used")
            return

        waiting_key.pop(uid)
        waiting_ip[uid] = text

        bot.send_message(m.chat.id, "✅ Key OK\nSend your IP:")
        return

    # ---------- IP ----------
    if uid in waiting_ip:

        if not valid_ip(text):
            bot.send_message(m.chat.id, "❌ Invalid IP")
            return

        key = waiting_ip[uid]

        cur.execute("""
        UPDATE keys
        SET used=1, used_by=?, ip=?, created_at=?
        WHERE key=?
        """, (uid, text, str(datetime.utcnow()), key))

        db.commit()

        waiting_ip.pop(uid)

        bot.send_message(m.chat.id, f"🎉 Activated\nIP: {text}")
        return

    # ---------- ADMIN ONLY ----------
    if not is_admin(uid):
        return

    # GENERATE KEY
    if text == "🔑 Generate Key":

        k = gen_key()

        cur.execute("INSERT INTO keys(key,created_at) VALUES(?,?)",
                    (k, str(datetime.utcnow())))
        db.commit()

        bot.send_message(m.chat.id, f"🔑 Key:\n{k}")
        return

    # LIST KEYS
    if text == "📋 All Keys":

        cur.execute("SELECT key,used FROM keys")
        rows = cur.fetchall()

        msg = "📋 Keys:\n\n"

        for k, u in rows:
            msg += f"{k} | {'USED' if u else 'FREE'}\n"

        bot.send_message(m.chat.id, msg)
        return

    # STATS
    if text == "📊 Statistics":

        cur.execute("SELECT COUNT(*) FROM keys")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM keys WHERE used=1")
        used = cur.fetchone()[0]

        bot.send_message(m.chat.id,
        f"📊 Stats\nTotal: {total}\nUsed: {used}")
        return

    # PROFILE
    if text == "👤 My Profile":
        bot.send_message(m.chat.id,
        f"ID: {uid}\nName: {m.from_user.first_name}")
        return

print("Bot Running...")
bot.infinity_polling()