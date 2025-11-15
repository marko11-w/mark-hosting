import os
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from yt_dlp import YoutubeDL

# ========== إعدادات عامة ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ تأكد من وضع TOKEN و WEBHOOK_URL في المتغيرات")

# ========== دوال مساعدة ==========
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write("{}")
    import json
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    import json
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid, username=""):
    users = load_users()
    if str(uid) not in users:
        users[str(uid)] = {"points": 0, "username": username}
        save_users(users)
    return users[str(uid)]

def set_points(uid, pts):
    users = load_users()
    users[str(uid)]["points"] = pts
    save_users(users)

def add_points(uid, pts):
    users = load_users()
    u = users.get(str(uid), {"points": 0})
    u["points"] += pts
    users[str(uid)] = u
    save_users(users)
    return u["points"]

# ========== الأوامر الأساسية ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id, user.username or "")
    kb = ReplyKeyboardMarkup(
        [["🎁 جمع النقاط", "📦 طلب رشق"], ["🎥 تحميل فيديو", "👤 حسابي"]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        f"مرحباً {user.first_name} 👋\n"
        "أنا بوت مارك الرسمي للرشق والنقاط 🔥\n"
        "اختر من الأزرار أدناه لبدء الاستخدام 👇",
        reply_markup=kb
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    await update.message.reply_text(
        f"👤 حسابك:\n"
        f"اليوزر: @{u.get('username','غير معروف')}\n"
        f"النقاط الحالية: {u.get('points',0)}"
    )

# ========== تحميل الفيديوهات ==========
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("📥 أرسل الرابط بعد الأمر: /download <link>")
        return
    url = args[0]
    msg = await update.message.reply_text("⏳ جاري التحميل...")
    ydl_opts = {"outtmpl": "downloads/%(title)s.%(ext)s"}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        await update.message.reply_document(document=open(filename, "rb"))
        await msg.edit_text("✅ تم التحميل بنجاح!")
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ أثناء التحميل: {e}")

# ========== نظام النقاط ==========
async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    new_points = add_points(user.id, 5)
    await update.message.reply_text(
        f"🎁 تم إضافة 5 نقاط لحسابك!\n"
        f"إجمالي نقاطك الآن: {new_points}"
    )

# ========== لوحة الأدمن ==========
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = (
        "👑 لوحة الأدمن - مارك\n\n"
        "/addpoints <id> <عدد> - لإضافة نقاط\n"
        "/setpoints <id> <عدد> - لتعيين نقاط\n"
        "/broadcast - إرسال رسالة جماعية\n"
        "/stats - عرض عدد المستخدمين"
    )
    await update.message.reply_text(text)

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("استخدم: /addpoints user_id amount")
        return
    uid, amount = int(args[0]), int(args[1])
    newp = add_points(uid, amount)
    await update.message.reply_text(f"✅ تم إضافة {amount} نقطة للمستخدم {uid}. المجموع الجديد: {newp}")

async def setpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("استخدم: /setpoints user_id amount")
        return
    uid, amount = int(args[0]), int(args[1])
    set_points(uid, amount)
    await update.message.reply_text(f"✅ تم تعيين نقاط المستخدم {uid} إلى {amount}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_users()
    await update.message.reply_text(f"📊 عدد المستخدمين المسجلين: {len(users)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["broadcast"] = True
    await update.message.reply_text("✉️ أرسل الآن الرسالة التي تريد إرسالها لجميع المستخدمين:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # بث جماعي
    if user.id == ADMIN_ID and context.user_data.get("broadcast"):
        context.user_data["broadcast"] = False
        users = load_users()
        sent = 0
        for uid in users.keys():
            try:
                await context.bot.send_message(int(uid), text)
                sent += 1
            except:
                pass
        await update.message.reply_text(f"✅ تم الإرسال إلى {sent} مستخدم.")
        return

    # القوائم
    if text == "🎁 جمع النقاط":
        await earn(update, context)
    elif text == "👤 حسابي":
        await profile(update, context)
    elif text == "🎥 تحميل فيديو":
        await update.message.reply_text("استخدم الأمر: /download <الرابط>")
    elif text == "📦 طلب رشق":
        await update.message.reply_text("🚀 أرسل تفاصيل طلب الرشق (رابط + نوع الخدمة)")
    else:
        await update.message.reply_text("اختر من الأزرار أو أرسل /start")

# ========== التشغيل عبر Webhook ==========
def main():
    application = Application.builder().token(TOKEN).build()

    # الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CommandHandler("earn", earn))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("addpoints", addpoints))
    application.add_handler(CommandHandler("setpoints", setpoints))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))

    # النصوص
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # تشغيل Webhook
    port = int(os.getenv("PORT", "8443"))
    logger.info("Starting webhook on port %s", port)
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )

if __name__ == "__main__":
    main()
