import os
import sqlite3
from datetime import datetime
from flask import Flask, request
import telebot
from telebot import types

# استبدل التوكن بتوكنك الجديد فوراً
TOKEN = os.environ.get("BOT_TOKEN", "8792298957:AAEKfuw-GprvOn62JsE-_MPkiCVojzV34OI")
ADMIN_ID = 8293515549
DB_PATH = "/tmp/database.db"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'ar',
            points INTEGER DEFAULT 0,
            last_day TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            details TEXT,
            invoice_url TEXT DEFAULT '',
            media_type TEXT DEFAULT 'text',
            media_id TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            code TEXT PRIMARY KEY,
            points INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            price INTEGER,
            date TEXT,
            status TEXT DEFAULT 'completed'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS force_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            channel_url TEXT,
            title TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    default_settings = {
        'bot_name': 'المتجر الذكي',
        'welcome_text': 'أهلاً بك في البوت الفاخر الخاص بنا. اختر من القائمة أدناه لتصفح المتجر:'
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

init_db()

def get_setting(key, default=""):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else default

def set_setting(key, value):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_user(user_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, lang, points, last_day FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, lang, points, last_day) VALUES (?, 'ar', 0, '')", (user_id,))
        conn.commit()
        cursor.execute("SELECT user_id, lang, points, last_day FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def add_points(user_id, points_to_add):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points_to_add, user_id))
    conn.commit()
    conn.close()

def check_subscription(user_id):
    if user_id == ADMIN_ID:
        return True, []
    
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_url, title FROM force_channels")
    channels = cursor.fetchall()
    conn.close()

    if not channels:
        return True, []

    unsubscribed = []
    for ch_id, ch_url, title in channels:
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                unsubscribed.append((ch_id, ch_url, title))
        except Exception:
            unsubscribed.append((ch_id, ch_url, title))

    if unsubscribed:
        return False, unsubscribed
    return True, []

def get_sub_keyboard(unsubscribed_channels):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch_id, ch_url, title in unsubscribed_channels:
        markup.add(types.InlineKeyboardButton(f"{title} ➲ ✨", url=ch_url))
    markup.add(types.InlineKeyboardButton("تأكيد الاشتراك ⚡ 🔄", callback_data="check_sub"))
    return markup

def main_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_prods = types.InlineKeyboardButton("المنتجات المتاحة 🛍️", callback_data="view_products")
    btn_profile = types.InlineKeyboardButton("حسابي ورصيدي 👤", callback_data="my_profile")
    btn_daily = types.InlineKeyboardButton("الهدية اليومية 🎁", callback_data="daily_gift")
    btn_charge = types.InlineKeyboardButton("شحن كود 💳", callback_data="charge_account")
    btn_lang = types.InlineKeyboardButton("تغيير اللغة 🌐", callback_data="change_lang")

    markup.add(btn_prods, btn_profile)
    markup.add(btn_daily, btn_charge)
    markup.add(btn_lang)

    if user_id == ADMIN_ID:
        btn_admin = types.InlineKeyboardButton("لوحة التحكم ⚙️", callback_data="admin_panel")
        markup.add(btn_admin)

    return markup

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add_prod = types.InlineKeyboardButton("إضافة منتج ➕", callback_data="adm_add_prod")
    btn_del_prod = types.InlineKeyboardButton("حذف منتج 🗑️", callback_data="adm_del_prod")
    btn_gen_card = types.InlineKeyboardButton("إنشاء كود 💳", callback_data="adm_gen_card")
    btn_add_pts = types.InlineKeyboardButton("تعديل النقاط 💰", callback_data="adm_mod_pts")
    btn_fsub = types.InlineKeyboardButton("اشتراك إجباري 📢", callback_data="adm_force_sub")
    btn_proof = types.InlineKeyboardButton("قناة الإثباتات 📜", callback_data="adm_proof_chan")
    btn_stats = types.InlineKeyboardButton("الإحصائيات 📊", callback_data="adm_stats")
    btn_bc = types.InlineKeyboardButton("إذاعة عامة 📢", callback_data="adm_broadcast")
    btn_customize = types.InlineKeyboardButton("تخصيص نصوص واسم البوت ✏️", callback_data="adm_customize")
    btn_back = types.InlineKeyboardButton("القائمة الرئيسية 🔙", callback_data="main_menu")

    markup.add(btn_add_prod, btn_del_prod)
    markup.add(btn_gen_card, btn_add_pts)
    markup.add(btn_fsub, btn_proof)
    markup.add(btn_stats, btn_bc)
    markup.add(btn_customize)
    markup.add(btn_back)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    get_user(user_id)

    is_sub, unsub_channels = check_subscription(user_id)
    bot_name = get_setting('bot_name', 'المتجر الذكي')
    
    if not is_sub:
        welcome_sub = (
            f"❖ ─── ✦ {bot_name} ✦ ─── ❖\n"
            f"👑 **مرحباً بك في بوت {bot_name}** 👑\n\n"
            f"⚠️ **عذراً عزيزي، يجب عليك الاشتراك في القنوات الرسمية لاستخدام البوت:**"
        )
        bot.send_message(
            message.chat.id,
            welcome_sub,
            reply_markup=get_sub_keyboard(unsub_channels),
            parse_mode="Markdown"
        )
        return

    welcome_custom = get_setting('welcome_text', 'أهلاً بك في البوت الفاخر الخاص بنا.')
    welcome_text = (
        f"❖ ─── ✦ {bot_name} ✦ ─── ❖\n"
        f"👑 **أهلاً بك في بوت {bot_name}** 👑\n"
        f"❖ ──────────────── ❖\n\n"
        f"{welcome_custom}"
    )

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=main_keyboard(user_id),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    bot_name = get_setting('bot_name', 'المتجر الذكي')

    if call.data == "check_sub":
        is_sub, unsub_channels = check_subscription(user_id)
        if is_sub:
            bot.answer_callback_query(call.id, f"✅ شكراً لاشتراكك! تم فتح بوت {bot_name}.", show_alert=True)
            welcome_custom = get_setting('welcome_text', 'أهلاً بك في البوت الفاخر الخاص بنا.')
            welcome_text = (
                f"❖ ─── ✦ {bot_name} ✦ ─── ❖\n"
                f"👑 **أهلاً بك في بوت {bot_name}** 👑\n"
                f"❖ ──────────────── ❖\n\n"
                f"{welcome_custom}"
            )
            bot.edit_message_text(
                welcome_text,
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=main_keyboard(user_id),
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في جميع القنوات بعد!", show_alert=True)
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=get_sub_keyboard(unsub_channels))
            except:
                pass
        return

    if user_id != ADMIN_ID:
        is_sub, unsub_channels = check_subscription(user_id)
        if not is_sub:
            bot.answer_callback_query(call.id, "⚠️ يجب عليك الاشتراك في القنوات أولاً!", show_alert=True)
            bot.send_message(chat_id, "⚠️ **يرجى الاشتراك في القنوات التالية لاستخدام البوت:**", reply_markup=get_sub_keyboard(unsub_channels), parse_mode="Markdown")
            return

    if call.data == "main_menu":
        welcome_custom = get_setting('welcome_text', 'أهلاً بك في البوت الفاخر الخاص بنا.')
        welcome_text = (
            f"❖ ─── ✦ {bot_name} ✦ ─── ❖\n"
            f"👑 **القائمة الرئيسية - {bot_name}** 👑\n"
            f"❖ ──────────────── ❖\n\n"
            f"{welcome_custom}"
        )
        bot.edit_message_text(
            welcome_text,
            chat_id=chat_id,
            message_id=msg_id,
