from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def owner_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 گروه‌ها و کانال‌های متصل", callback_data="chats")],
        [InlineKeyboardButton(text="🔗 ساخت لینک دعوت", callback_data="invite_menu")],
        [InlineKeyboardButton(text="📊 آمار کلی", callback_data="stats")],
        [InlineKeyboardButton(text="🛡 راهنمای مدیریت", callback_data="help")],
    ])

def chat_picker(chats, prefix="pick"):
    rows = []
    for c in chats:
        title = (c["title"] or str(c["chat_id"]))[:35]
        rows.append([InlineKeyboardButton(
            text=f"{'👥' if c['chat_type'] in ('group','supergroup') else '📢'} {title}",
            callback_data=f"{prefix}:{c['chat_id']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
