import re
import time
from collections import defaultdict, deque
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.exceptions import TelegramAPIError
from keyboards import owner_menu, chat_picker

router = Router()
_flood = defaultdict(deque)
_url_re = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/)", re.I)

def is_owner(user_id, settings):
    return user_id == settings.owner_id

async def is_chat_admin(message: Message) -> bool:
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except TelegramAPIError:
        return False

@router.message(CommandStart(), F.chat.type == "private")
async def start(message: Message, settings):
    if not is_owner(message.from_user.id, settings):
        await message.answer("سلام! این ربات در حال حاضر خصوصی است و فقط مالک می‌تواند پنل مدیریت را باز کند.")
        return
    await message.answer(
        f"سلام مدیر عزیز 👋\nبه پنل <b>{settings.bot_name}</b> خوش آمدی.\n\n"
        "برای مدیریت، یکی از گزینه‌های زیر را انتخاب کن. ابتدا ربات را به گروه‌ها و کانال‌ها اضافه و مدیر کن.",
        reply_markup=owner_menu()
    )

@router.callback_query(F.data == "home")
async def home(call: CallbackQuery, settings):
    if not is_owner(call.from_user.id, settings):
        return await call.answer("دسترسی ندارید.", show_alert=True)
    await call.message.edit_text("🏠 پنل اصلی مدیریت", reply_markup=owner_menu())
    await call.answer()

@router.callback_query(F.data == "chats")
async def chats(call: CallbackQuery, db, settings):
    if not is_owner(call.from_user.id, settings):
        return await call.answer("دسترسی ندارید.", show_alert=True)
    rows = await db.fetchall("SELECT * FROM chats WHERE is_active=1 ORDER BY added_at DESC")
    if not rows:
        await call.message.edit_text(
            "هنوز گروه یا کانالی ثبت نشده است.\nربات را به گروه/کانال اضافه کن و دسترسی مدیریتی بده.",
            reply_markup=owner_menu()
        )
    else:
        await call.message.edit_text(
            f"📚 موارد متصل: {len(rows)}\nبرای ساخت لینک دعوت، یک گروه را انتخاب کن.",
            reply_markup=chat_picker(rows)
        )
    await call.answer()

@router.callback_query(F.data == "invite_menu")
async def invite_menu(call: CallbackQuery, db, settings):
    if not is_owner(call.from_user.id, settings):
        return await call.answer("دسترسی ندارید.", show_alert=True)
    rows = await db.fetchall("SELECT * FROM chats WHERE is_active=1 AND chat_type IN ('group','supergroup')")
    if not rows:
        await call.message.edit_text("گروهی برای ساخت لینک دعوت ثبت نشده است.", reply_markup=owner_menu())
    else:
        await call.message.edit_text("گروه موردنظر برای ساخت لینک دعوت را انتخاب کن:", reply_markup=chat_picker(rows, "invite"))
    await call.answer()

@router.callback_query(F.data.startswith("invite:"))
async def create_invite(call: CallbackQuery, db, settings):
    if not is_owner(call.from_user.id, settings):
        return await call.answer("دسترسی ندارید.", show_alert=True)
    chat_id = int(call.data.split(":", 1)[1])
    try:
        link = await call.bot.create_chat_invite_link(
            chat_id=chat_id, name=f"GM campaign {int(time.time())}"
        )
        await db.execute(
            "INSERT INTO invite_links(chat_id,invite_link,label,created_by) VALUES(?,?,?,?)",
            (chat_id, link.invite_link, "Owner campaign", call.from_user.id)
        )
        await call.message.answer(f"🔗 لینک دعوت ساخته شد:\n{link.invite_link}\n\nاین لینک را برای کمپین مشخص استفاده کن.")
    except TelegramAPIError as e:
        await call.message.answer(f"ساخت لینک ناموفق بود. بررسی کن ربات مدیر گروه و دارای دسترسی دعوت اعضا باشد.\n\nجزئیات: {e}")
    await call.answer()

@router.callback_query(F.data == "stats")
async def stats(call: CallbackQuery, db, settings):
    if not is_owner(call.from_user.id, settings):
        return await call.answer("دسترسی ندارید.", show_alert=True)
    chats = await db.fetchone("SELECT COUNT(*) AS n FROM chats WHERE is_active=1")
    members = await db.fetchone("SELECT COUNT(*) AS n FROM members WHERE status='member'")
    warns = await db.fetchone("SELECT COUNT(*) AS n FROM warnings")
    await call.message.edit_text(
        "📊 <b>آمار ثبت‌شده</b>\n"
        f"گروه‌ها و کانال‌های متصل: <b>{chats['n']}</b>\n"
        f"اعضای ثبت‌شده در رویدادها: <b>{members['n']}</b>\n"
        f"اخطارهای ثبت‌شده: <b>{warns['n']}</b>\n\n"
        "این آمار از زمان اتصال ربات جمع‌آوری می‌شود و الزاماً برابر کل اعضای فعلی تلگرام نیست.",
        reply_markup=owner_menu()
    )
    await call.answer()

@router.callback_query(F.data == "help")
async def help_panel(call: CallbackQuery, settings):
    if not is_owner(call.from_user.id, settings):
        return await call.answer("دسترسی ندارید.", show_alert=True)
    await call.message.edit_text(
        "🛡 <b>راهنمای راه‌اندازی</b>\n"
        "۱) ربات را به گروه اضافه کن.\n۲) دسترسی حذف پیام، محدودکردن اعضا و دعوت اعضا را بده.\n"
        "۳) برای فیلتر پیام‌های عادی، Privacy Mode را در BotFather خاموش کن.\n"
        "۴) برای مدیریت، دستورهای /warn، /mute، /ban و /unban را در گروه استفاده کن.\n\n"
        "دستورها باید در پاسخ به پیام کاربر اجرا شوند.",
        reply_markup=owner_menu()
    )
    await call.answer()

@router.my_chat_member()
async def bot_added(event: ChatMemberUpdated, db):
    chat = event.chat
    new_status = event.new_chat_member.status
    if new_status in ("member", "administrator"):
        await db.upsert_chat(chat)
        await db.log(chat.id, event.from_user.id, "bot_added", new_status)
    elif new_status in ("kicked", "left"):
        await db.execute("UPDATE chats SET is_active=0 WHERE chat_id=?", (chat.id,))
        await db.log(chat.id, event.from_user.id, "bot_removed", new_status)

@router.chat_member()
async def member_update(event: ChatMemberUpdated, db):
    chat = event.chat
    old = event.old_chat_member.status
    new = event.new_chat_member.status
    user = event.new_chat_member.user
    if user.is_bot:
        return
    if new in ("member", "administrator", "creator") and old in ("left", "kicked"):
        await db.execute(
            """INSERT INTO members(chat_id,user_id,username,first_name,status,left_at)
               VALUES(?,?,?,?, 'member', NULL)
               ON CONFLICT(chat_id,user_id) DO UPDATE SET username=excluded.username,
               first_name=excluded.first_name,status='member',left_at=NULL""",
            (chat.id, user.id, user.username, user.first_name)
        )
        await db.log(chat.id, user.id, "member_joined", event.invite_link.invite_link if event.invite_link else "")
    elif new in ("left", "kicked"):
        await db.execute(
            "UPDATE members SET status=?,left_at=CURRENT_TIMESTAMP WHERE chat_id=? AND user_id=?",
            (new, chat.id, user.id)
        )
        await db.log(chat.id, user.id, "member_left", new)


@router.message(F.new_chat_members)
async def welcome(message: Message, settings):
    if not settings.welcome_enabled:
        return
    for user in message.new_chat_members:
        if not user.is_bot:
            await message.answer(f"خوش آمدی {user.mention_html()} 🌷\nلطفاً قوانین گروه را رعایت کن.")

async def target_from_reply(message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("این دستور را در پاسخ به پیام کاربر اجرا کن.")
        return None
    return message.reply_to_message.from_user

@router.message(Command("warn"), F.chat.type.in_({"group", "supergroup"}))
async def warn(message: Message, db):
    if not await is_chat_admin(message):
        return await message.reply("فقط مدیران گروه می‌توانند این دستور را اجرا کنند.")
    target = await target_from_reply(message)
    if not target: return
    reason = (message.text or "").partition(" ")[2] or "بدون توضیح"
    await db.execute("INSERT INTO warnings(chat_id,user_id,admin_id,reason) VALUES(?,?,?,?)",
                     (message.chat.id, target.id, message.from_user.id, reason))
    row = await db.fetchone("SELECT COUNT(*) AS n FROM warnings WHERE chat_id=? AND user_id=?",
                            (message.chat.id, target.id))
    await message.reply(f"⚠️ به {target.mention_html()} اخطار داده شد. تعداد اخطارها: {row['n']}")

@router.message(Command("mute"), F.chat.type.in_({"group", "supergroup"}))
async def mute(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("فقط مدیران گروه می‌توانند این دستور را اجرا کنند.")
    target = await target_from_reply(message)
    if not target: return
    try:
        from datetime import datetime, timedelta, timezone
        until = datetime.now(timezone.utc) + timedelta(minutes=10)
        await message.bot.restrict_chat_member(message.chat.id, target.id,
            permissions=__import__("aiogram").types.ChatPermissions(can_send_messages=False),
            until_date=until)
        await message.reply(f"🔇 {target.mention_html()} برای ۱۰ دقیقه محدود شد.")
    except TelegramAPIError as e:
        await message.reply(f"عملیات ناموفق بود: {e}")

@router.message(Command("ban"), F.chat.type.in_({"group", "supergroup"}))
async def ban(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("فقط مدیران گروه می‌توانند این دستور را اجرا کنند.")
    target = await target_from_reply(message)
    if not target: return
    try:
        await message.bot.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"⛔ {target.mention_html()} مسدود شد.")
    except TelegramAPIError as e:
        await message.reply(f"عملیات ناموفق بود: {e}")

@router.message(Command("unban"), F.chat.type.in_({"group", "supergroup"}))
async def unban(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("فقط مدیران گروه می‌توانند این دستور را اجرا کنند.")
    target = await target_from_reply(message)
    if not target: return
    try:
        await message.bot.unban_chat_member(message.chat.id, target.id, only_if_banned=True)
        await message.reply(f"✅ محدودیت بن {target.mention_html()} برداشته شد.")
    except TelegramAPIError as e:
        await message.reply(f"عملیات ناموفق بود: {e}")

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_moderation(message: Message, db, settings):
    if not message.from_user or message.from_user.is_bot:
        return
    if await is_chat_admin(message):
        return

    text = message.text or message.caption or ""
    reason = None

    if settings.anti_link and _url_re.search(text):
        reason = "لینک غیرمجاز"
    elif any(word in text.lower() for word in settings.blocked_words):
        reason = "استفاده از کلمه ممنوع"

    if settings.anti_flood:
        key = (message.chat.id, message.from_user.id)
        now = time.monotonic()
        q = _flood[key]
        q.append(now)
        while q and now - q[0] > settings.flood_window_seconds:
            q.popleft()
        if len(q) > settings.flood_max_messages:
            reason = "ارسال پیام‌های بیش از حد"

    if reason:
        try:
            await message.delete()
            await db.log(message.chat.id, message.from_user.id, "message_removed", reason)
            await message.answer(f"⚠️ پیام {message.from_user.mention_html()} حذف شد: {reason}")
        except TelegramAPIError:
            pass
        return

