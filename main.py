import os
import logging
from pathlib import Path

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

from utils import (
    get_user,
    add_points,
    set_points,
    get_all_users,
    create_order,
    get_stats,
    load_channels,
    mark_channel_rewarded,
    has_channel_rewarded,
)

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Env vars ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID") or "0")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://mark-hosting-production.up.railway.app

if not TOKEN:
    raise RuntimeError("Missing TOKEN env var")
if not WEBHOOK_URL:
    raise RuntimeError("Missing WEBHOOK_URL env var")

# --- Downloads folder & yt-dlp options ---
Path("downloads").mkdir(exist_ok=True)
YDL_OPTS = {"outtmpl": "downloads/%(id)s.%(ext)s", "quiet": True}


# ---------- Keyboards ----------

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🏠 الرئيسية", "💰 حسابي"],
            ["🎁 جمع النقاط", "📦 طلب رشق"],
            ["🎥 تحميل فيديو", "📞 الدعم"],
        ],
        resize_keyboard=True,
    )


# ---------- User commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command and main menu."""
    user = update.effective_user
    u = get_user(user.id, user.username or "")

    welcome_line = ""
    if not u.get("welcome_points_given"):
        new_points = add_points(user.id, 10)
        u = get_user(user.id)
        u["welcome_points_given"] = True
        set_points(user.id, u["points"])
        welcome_line = f"🥳 حصلت على 10 نقاط هدية! (إجمالي نقاطك الآن: {new_points})\n\n"

    text = (
        f"مرحباً {user.first_name} في بوت مارك للرشق والنقاط 🔥\n"
        "من خلال النقاط يمكنك طلب رشق:\n"
        "- متابعين انستغرام\n"
        "- متابعين تيك توك\n"
        "- أعضاء مجموعات تيليجرام\n\n"
        f"{welcome_line}"
        "اختر ما تريد من الأزرار 👇"
    )
    await update.message.reply_text(text, reply_markup=main_menu_kb())


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    u = get_user(user.id, user.username or "")
    txt = (
        "💰 حسابك:\n"
        f"- اليوزر: @{u.get('username') or 'بدون'}\n"
        f"- عدد النقاط: {u.get('points', 0)}\n"
    )
    await update.message.reply_text(txt, reply_markup=main_menu_kb())


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # عدّل هذه البيانات ليوزرك وقناتك
    txt = (
        "📞 الدعم:\n"
        "للتواصل مع دعم مارك رشق:\n"
        "@YourSupportUsername\n"
        "أو قناة مارك الرسمية:\n"
        "https://t.me/YourChannelUsername"
    )
    await update.message.reply_text(txt, reply_markup=main_menu_kb())


# ---------- Earn points via channels ----------

async def earn_points_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channels = load_channels()
    if not channels:
        await update.message.reply_text(
            "حالياً لا توجد قنوات متاحة لجمع النقاط.\n"
            "تواصل مع الأدمن لإضافتها.",
            reply_markup=main_menu_kb(),
        )
        return

    lines = ["🎁 قنوات متاحة لجمع النقاط:\n"]
    rows = []
    for idx, ch in enumerate(channels):
        lines.append(f"- {ch['title']} | مكافأة: {ch['reward']} نقطة")
        rows.append([
            InlineKeyboardButton("📲 فتح القناة", url=ch["link"]),
            InlineKeyboardButton("✅ تحقّق", callback_data=f"check_channel:{idx}"),
        ])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def handle_channel_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    user_id = user.id

    try:
        _, idx_str = data.split(":")
        idx = int(idx_str)
    except Exception:
        await query.edit_message_text("❌ قناة غير صالحة.")
        return

    channels = load_channels()
    if idx < 0 or idx >= len(channels):
        await query.edit_message_text("❌ قناة غير موجودة.")
        return

    ch = channels[idx]
    ch_id = ch["id"]
    reward = ch["reward"]

    # سبق حصل نقاط من هذه القناة؟
    if has_channel_rewarded(user_id, ch_id):
        await query.edit_message_text(
            f"✅ سبق أن حصلت على نقاط قناة {ch['title']}."
        )
        return

    # التحقق الحقيقي من الاشتراك
    try:
        member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
        status = member.status
        if status in ("member", "administrator", "creator"):
            new_points = add_points(user_id, reward)
            mark_channel_rewarded(user_id, ch_id)
            await query.edit_message_text(
                f"🎉 تم التحقق من اشتراكك في {ch['title']}.\n"
                f"تم إضافة {reward} نقطة.\n"
                f"إجمالي نقاطك الآن: {new_points}"
            )
        else:
            await query.edit_message_text(
                "❌ يبدو أنك لم تشترك بعد في القناة.\n"
                "ادخل للقناة، اشترك، ثم اضغط تحقّق مرة أخرى."
            )
    except Exception as e:
        logger.error("Error in get_chat_member: %s", e)
        await query.edit_message_text(
            "⚠️ حدث خطأ أثناء التحقق من الاشتراك.\n"
            "تأكد أن البوت أدمن في القناة أو أن القناة عامة."
        )


# ---------- Rshq orders ----------

async def start_rshq_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    get_user(user.id, user.username or "")

    kb = [
        [InlineKeyboardButton("📸 متابعين انستغرام", callback_data="srv:instagram_followers")],
        [InlineKeyboardButton("🎵 متابعين تيك توك", callback_data="srv:tiktok_followers")],
        [InlineKeyboardButton("👥 أعضاء مجموعة تيليجرام", callback_data="srv:telegram_members")],
    ]
    await update.message.reply_text(
        "اختر نوع الرشق الذي تريد طلبه:",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def rshq_service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("srv:"):
        return

    service = data.split(":", 1)[1]
    context.user_data["order_state"] = "awaiting_target"
    context.user_data["order"] = {"service": service}

    await query.edit_message_text(
        "أرسل الآن رابط الحساب / اليوزر / رابط المجموعة التي تريد الرشق لها:"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text.strip()

    # بث أدمن؟
    if user.id == ADMIN_ID and context.user_data.get("admin_broadcast_pending"):
        await handle_admin_broadcast_message(update, context)
        return

    state = context.user_data.get("order_state")

    # خطوة الهدف
    if state == "awaiting_target":
        context.user_data["order"]["target"] = text
        context.user_data["order_state"] = "awaiting_quantity"
        await update.message.reply_text(
            "كمية الرشق المطلوبة؟ (اكتب رقم فقط، مثال: 1000)"
        )
        return

    # خطوة الكمية
    if state == "awaiting_quantity":
        if not text.isdigit():
            await update.message.reply_text("❌ رجاءً أرسل رقم فقط للكمية.")
            return
        qty = int(text)
        order = context.user_data["order"]
        order["quantity"] = qty

        # تسعير بسيط: نقطة لكل 10 وحدات
        cost = max(1, qty // 10)

        u = get_user(user.id, user.username or "")
        points = u.get("points", 0)
        if points < cost:
            await update.message.reply_text(
                f"❌ نقاطك غير كافية.\n"
                f"الكمية: {qty}\n"
                f"التكلفة: {cost} نقطة\n"
                f"نقاطك الحالية: {points}"
            )
            context.user_data["order_state"] = None
            context.user_data["order"] = None
            return

        # خصم النقاط وحفظ الطلب
        set_points(user.id, points - cost)
        order_id = create_order(
            user.id, order["service"], order["target"], qty, cost
        )

        context.user_data["order_state"] = None
        context.user_data["order"] = None

        await update.message.reply_text(
            f"✅ تم تسجيل طلب الرشق رقم #{order_id}\n"
            f"الخدمة: {order['service']}\n"
            f"الهدف: {order['target']}\n"
            f"الكمية: {qty}\n"
            f"التكلفة: {cost} نقطة\n\n"
            "سيتم تنفيذ الطلب من قبل الأدمن في أقرب وقت ✅",
            reply_markup=main_menu_kb(),
        )
        return

    # أزرار القائمة الرئيسية
    if text == "🏠 الرئيسية":
        await start(update, context)
    elif text == "💰 حسابي":
        await profile(update, context)
    elif text == "🎁 جمع النقاط":
        await earn_points_menu(update, context)
    elif text == "📦 طلب رشق":
        await start_rshq_order(update, context)
    elif text == "🎥 تحميل فيديو":
        await update.message.reply_text(
            "أرسل الأمر:\n/download <الرابط>\nأو أرسل الرابط مباشرة."
        )
    elif text == "📞 الدعم":
        await support(update, context)
    elif text.startswith("http"):
        # رابط فيديو مباشرة
        await download_command(update, context)
    else:
        await update.message.reply_text(
            "اختر من الأزرار في الأسفل أو أرسل /start لإعادة القائمة.",
            reply_markup=main_menu_kb(),
        )


# ---------- Video download ----------

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    url = None
    if args:
        url = args[0]
    elif update.message and update.message.text.startswith("http"):
        url = update.message.text.strip()

    if not url:
        await update.message.reply_text("📥 أرسل الرابط بعد الأمر: /download <link>")
        return

    msg = await update.message.reply_text("⏳ جاري التحميل...")
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        await update.message.reply_document(document=open(filename, "rb"))
        await msg.edit_text("✅ تم التحميل بنجاح!")
    except Exception as e:
        logger.error("download error: %s", e)
        await msg.edit_text(f"❌ فشل التحميل: {e}")


# ---------- Admin commands ----------

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    stats = get_stats()
    text = (
        "👑 لوحة الأدمن - مارك\n"
        f"- عدد المستخدمين: {stats['users_count']}\n"
        f"- إجمالي الطلبات: {stats['orders_count']}\n"
        f"- الطلبات المعلقة: {stats['pending_orders']}\n\n"
        "الأوامر:\n"
        "/stats - إحصائيات\n"
        "/orders - آخر الطلبات\n"
        "/broadcast - رسالة جماعية\n"
        "/addpoints user_id amount - إضافة نقاط\n"
        "/setpoints user_id amount - تعيين نقاط\n"
        "/setreward channel_id reward - تعيين مكافأة قناة\n"
    )
    await update.message.reply_text(text)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    stats = get_stats()
    await update.message.reply_text(
        f"📊 إحصائيات:\n"
        f"- عدد المستخدمين: {stats['users_count']}\n"
        f"- إجمالي الطلبات: {stats['orders_count']}\n"
        f"- الطلبات المعلقة: {stats['pending_orders']}\n",
    )


async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    stats = get_stats()
    orders = stats["orders"]
    if not orders:
        await update.message.reply_text("لا توجد طلبات حتى الآن.")
        return
    lines = []
    for o in orders[-20:]:
        lines.append(
            f"#{o['id']} | user:{o['user_id']} | {o['service']} | qty:{o['quantity']} | "
            f"cost:{o['cost']} | status:{o['status']}"
        )
    await update.message.reply_text("آخر الطلبات:\n" + "\n".join(lines))


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["admin_broadcast_pending"] = True
    await update.message.reply_text(
        "اكتب الآن الرسالة التي تريد إرسالها لكل المستخدمين:"
    )


async def handle_admin_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["admin_broadcast_pending"] = False
    text = update.message.text
    users = get_all_users()
    sent = 0
    failed = 0
    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"تم إرسال الرسالة.\n✔️ ناجحة: {sent}\n❌ فاشلة: {failed}"
    )


async def addpoints_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("استخدم: /addpoints user_id amount")
        return
    uid = int(args[0])
    amount = int(args[1])
    newp = add_points(uid, amount)
    await update.message.reply_text(
        f"تم إضافة {amount} نقطة للمستخدم {uid}.\nالنقاط الجديدة: {newp}"
    )


async def setpoints_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("استخدم: /setpoints user_id amount")
        return
    uid = int(args[0])
    amount = int(args[1])
    newp = set_points(uid, amount)
    await update.message.reply_text(
        f"تم تعيين نقاط المستخدم {uid} إلى {newp} نقطة."
    )


async def setreward_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: set reward points for a channel id (which exists in channels.json)."""
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("استخدم: /setreward channel_id reward")
        return
    try:
        ch_id = int(args[0])
        reward = int(args[1])
    except ValueError:
        await update.message.reply_text("channel_id و reward يجب أن يكونا أرقام.")
        return

    channels = load_channels()
    found = False
    for ch in channels:
        if int(ch["id"]) == ch_id:
            ch["reward"] = reward
            found = True
            break
    if not found:
        await update.message.reply_text("❌ لم يتم العثور على هذه القناة في channels.json")
        return

    # حفظ القنوات بعد التعديل
    from utils import CHANNELS_FILE  # لتجنب الدوران في الاستيراد
    import json as _json
    CHANNELS_FILE.write_text(
        _json.dumps(channels, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    await update.message.reply_text(
        f"✅ تم تعيين مكافأة القناة {ch_id} إلى {reward} نقطة."
    )


# ---------- Main / webhook ----------

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("download", download_command))

    # Admin commands
    application.add_handler(CommandHandler("admin", admin_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("orders", orders_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CommandHandler("addpoints", addpoints_cmd))
    application.add_handler(CommandHandler("setpoints", setpoints_cmd))
    application.add_handler(CommandHandler("setreward", setreward_cmd))

    # Callback queries
    application.add_handler(CallbackQueryHandler(handle_channel_check, pattern="^check_channel:"))
    application.add_handler(CallbackQueryHandler(rshq_service_selected, pattern="^srv:"))

    # Text handler (menu + flows)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

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
