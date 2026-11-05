const API = (token) => `https://api.telegram.org/bot${token}`;

async function tg(env, method, payload = {}) {
  const res = await fetch(`${API(env.BOT_TOKEN)}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!data.ok) throw new Error(data.description || `Telegram API ${method} failed`);
  return data.result;
}

const esc = (s = "") => String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const nameOf = (u = {}) => [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username || String(u.id || "");
const mention = (u = {}) => `<a href="tg://user?id=${u.id}">${esc(nameOf(u))}</a>`;
const isGroup = (chat) => chat && ["group", "supergroup"].includes(chat.type);
const ownerOnly = (u, env) => Number(u?.id) === Number(env.OWNER_ID);

async function answer(env, chat_id, text, extra = {}) {
  return tg(env, "sendMessage", { chat_id, text, parse_mode: "HTML", ...extra });
}
async function callbackAnswer(env, id, text = "", alert = false) {
  return tg(env, "answerCallbackQuery", { callback_query_id: id, text, show_alert: alert });
}
async function editOrSend(env, chat_id, message_id, text, reply_markup) {
  try {
    return await tg(env, "editMessageText", { chat_id, message_id, text, parse_mode: "HTML", reply_markup });
  } catch {
    return answer(env, chat_id, text, { reply_markup });
  }
}
const menu = () => ({ inline_keyboard: [
  [{ text: "👥 گروه‌ها و کانال‌های متصل", callback_data: "chats" }],
  [{ text: "🔗 ساخت لینک دعوت", callback_data: "invite_menu" }],
  [{ text: "📊 آمار کلی", callback_data: "stats" }],
  [{ text: "🛡 راهنمای مدیریت", callback_data: "help" }],
] });
const back = () => ({ inline_keyboard: [[{ text: "⬅️ بازگشت", callback_data: "home" }]] });

async function saveChat(env, chat) {
  await env.DB.prepare(`INSERT INTO chats(chat_id,title,chat_type,username,is_active)
    VALUES(?,?,?,?,1) ON CONFLICT(chat_id) DO UPDATE SET
    title=excluded.title, chat_type=excluded.chat_type, username=excluded.username, is_active=1`)
    .bind(chat.id, chat.title || String(chat.id), chat.type, chat.username || null).run();
}
async function logEvent(env, chatId, actorId, event, details = "") {
  await env.DB.prepare("INSERT INTO activity_logs(chat_id,actor_id,event,details) VALUES(?,?,?,?)")
    .bind(chatId ?? null, actorId ?? null, event, String(details)).run();
}
async function isAdmin(env, chatId, userId) {
  try {
    const m = await tg(env, "getChatMember", { chat_id: chatId, user_id: userId });
    return ["administrator", "creator"].includes(m.status);
  } catch { return false; }
}
async function ownerStart(env, msg) {
  if (!ownerOnly(msg.from, env)) return answer(env, msg.chat.id, "سلام! این ربات خصوصی است و فقط مالک اجازه استفاده از پنل را دارد.");
  return answer(env, msg.chat.id,
    `سلام مدیر عزیز 👋\nبه پنل <b>${esc(env.BOT_NAME || "Growth Manager")}</b> خوش آمدی.\n\nربات را به گروه‌ها و کانال‌ها اضافه و مدیر کن.`,
    { reply_markup: menu() });
}
async function showChats(env, msg, edit = false, invite = false) {
  const sql = invite
    ? "SELECT * FROM chats WHERE is_active=1 AND chat_type IN ('group','supergroup') ORDER BY added_at DESC"
    : "SELECT * FROM chats WHERE is_active=1 ORDER BY added_at DESC";
  const { results = [] } = await env.DB.prepare(sql).all();
  if (!results.length) return answer(env, msg.chat.id, invite ? "گروهی برای ساخت لینک دعوت ثبت نشده است." : "هنوز گروه یا کانالی ثبت نشده است. ربات را اضافه و مدیر کن.", { reply_markup: menu() });
  const rows = results.slice(0, 50).map(c => [{
    text: `${["group","supergroup"].includes(c.chat_type) ? "👥" : "📢"} ${(c.title || c.chat_id).slice(0, 35)}`,
    callback_data: `invite:${c.chat_id}`,
  }]);
  rows.push([{ text: "⬅️ بازگشت", callback_data: "home" }]);
  return answer(env, msg.chat.id, invite ? "گروه موردنظر را برای ساخت لینک دعوت انتخاب کن:" : `📚 موارد متصل: ${results.length}\nبرای ساخت لینک دعوت، یک گروه را انتخاب کن.`, { reply_markup: { inline_keyboard: rows } });
}
async function handleCallback(env, q) {
  const u = q.from;
  if (!ownerOnly(u, env)) return callbackAnswer(env, q.id, "دسترسی ندارید.", true);
  const data = q.data || "";
  const m = q.message;
  if (data === "home") {
    await editOrSend(env, m.chat.id, m.message_id, "🏠 پنل اصلی مدیریت", menu());
  } else if (data === "chats") {
    const { results = [] } = await env.DB.prepare("SELECT * FROM chats WHERE is_active=1 ORDER BY added_at DESC").all();
    const rows = results.slice(0, 50).map(c => [{ text: `${["group","supergroup"].includes(c.chat_type) ? "👥" : "📢"} ${(c.title || c.chat_id).slice(0,35)}`, callback_data: `noop:${c.chat_id}` }]);
    rows.push([{ text: "⬅️ بازگشت", callback_data: "home" }]);
    await editOrSend(env, m.chat.id, m.message_id, results.length ? `📚 گروه‌ها و کانال‌های متصل: ${results.length}` : "هنوز گروه یا کانالی ثبت نشده است. ربات را اضافه و مدیر کن.", { inline_keyboard: rows });
  } else if (data === "invite_menu") {
    const { results = [] } = await env.DB.prepare("SELECT * FROM chats WHERE is_active=1 AND chat_type IN ('group','supergroup') ORDER BY added_at DESC").all();
    const rows = results.slice(0,50).map(c => [{ text: `👥 ${(c.title || c.chat_id).slice(0,35)}`, callback_data: `invite:${c.chat_id}` }]);
    rows.push([{ text: "⬅️ بازگشت", callback_data: "home" }]);
    await editOrSend(env, m.chat.id, m.message_id, results.length ? "گروه موردنظر برای ساخت لینک دعوت را انتخاب کن:" : "گروهی برای ساخت لینک دعوت ثبت نشده است.", { inline_keyboard: rows });
  } else if (data.startsWith("invite:")) {
    const chatId = Number(data.split(":")[1]);
    try {
      const link = await tg(env, "createChatInviteLink", { chat_id: chatId, name: `Campaign ${Date.now()}` });
      await env.DB.prepare("INSERT INTO invite_links(chat_id,invite_link,label,created_by) VALUES(?,?,?,?)")
        .bind(chatId, link.invite_link, "Owner campaign", u.id).run();
      await answer(env, m.chat.id, `🔗 لینک دعوت ساخته شد:\n${esc(link.invite_link)}\n\nاین لینک را برای کمپین مشخص استفاده کن.`);
    } catch (e) {
      await answer(env, m.chat.id, `ساخت لینک ناموفق بود. بررسی کن ربات مدیر گروه و دارای دسترسی دعوت اعضا باشد.\n\n${esc(e.message)}`);
    }
  } else if (data === "stats") {
    const chats = await env.DB.prepare("SELECT COUNT(*) n FROM chats WHERE is_active=1").first();
    const members = await env.DB.prepare("SELECT COUNT(*) n FROM members WHERE status='member'").first();
    const warns = await env.DB.prepare("SELECT COUNT(*) n FROM warnings").first();
    await editOrSend(env, m.chat.id, m.message_id,
      `📊 <b>آمار ثبت‌شده</b>\nگروه‌ها و کانال‌های متصل: <b>${chats.n}</b>\nاعضای ثبت‌شده در رویدادها: <b>${members.n}</b>\nاخطارهای ثبت‌شده: <b>${warns.n}</b>\n\nاین آمار از زمان اتصال ربات جمع‌آوری می‌شود.`,
      menu());
  } else if (data === "help") {
    await editOrSend(env, m.chat.id, m.message_id,
      "🛡 <b>راهنمای مدیریت</b>\n۱) ربات را به گروه اضافه و مدیر کن.\n۲) دسترسی حذف پیام، محدودکردن اعضا و دعوت اعضا را بده.\n۳) برای دریافت پیام‌های عادی، Privacy Mode را در BotFather خاموش کن.\n۴) دستورهای /warn، /mute، /ban و /unban را در پاسخ به پیام کاربر اجرا کن.",
      menu());
  } else if (data.startsWith("noop:")) {
    await callbackAnswer(env, q.id, "این گروه متصل است.");
    return;
  }
  await callbackAnswer(env, q.id);
}
async function handleMemberUpdate(env, upd) {
  const cm = upd.my_chat_member;
  if (cm) {
    const chat = cm.chat, status = cm.new_chat_member.status;
    if (["member", "administrator"].includes(status)) {
      await saveChat(env, chat);
      await logEvent(env, chat.id, cm.from.id, "bot_added", status);
    } else if (["kicked", "left"].includes(status)) {
      await env.DB.prepare("UPDATE chats SET is_active=0 WHERE chat_id=?").bind(chat.id).run();
      await logEvent(env, chat.id, cm.from.id, "bot_removed", status);
    }
    return;
  }
  const ev = upd.chat_member;
  if (!ev) return;
  const oldS = ev.old_chat_member.status, newS = ev.new_chat_member.status;
  const user = ev.new_chat_member.user, chat = ev.chat;
  if (user.is_bot) return;
  if (["member","administrator","creator"].includes(newS) && ["left","kicked"].includes(oldS)) {
    await env.DB.prepare(`INSERT INTO members(chat_id,user_id,username,first_name,status,left_at)
      VALUES(?,?,?,?, 'member', NULL) ON CONFLICT(chat_id,user_id) DO UPDATE SET
      username=excluded.username, first_name=excluded.first_name, status='member', left_at=NULL`)
      .bind(chat.id, user.id, user.username || null, user.first_name || "").run();
    await logEvent(env, chat.id, user.id, "member_joined", ev.invite_link?.invite_link || "");
  } else if (["left","kicked"].includes(newS)) {
    await env.DB.prepare("UPDATE members SET status=?,left_at=CURRENT_TIMESTAMP WHERE chat_id=? AND user_id=?")
      .bind(newS, chat.id, user.id).run();
    await logEvent(env, chat.id, user.id, "member_left", newS);
  }
}
async function handleGroupMessage(env, msg) {
  if (!msg.from || msg.from.is_bot || !isGroup(msg.chat)) return;
  const text = msg.text || msg.caption || "";
  const cmd = text.trim().split(/\s+/, 1)[0].split("@")[0].toLowerCase();

  if (["/warn","/mute","/ban","/unban"].includes(cmd)) {
    if (!await isAdmin(env, msg.chat.id, msg.from.id))
      return answer(env, msg.chat.id, "فقط مدیران گروه می‌توانند این دستور را اجرا کنند.", { reply_to_message_id: msg.message_id });
    const target = msg.reply_to_message?.from;
    if (!target) return answer(env, msg.chat.id, "این دستور را در پاسخ به پیام کاربر اجرا کن.", { reply_to_message_id: msg.message_id });
    const reason = text.trim().split(/\s+/).slice(1).join(" ") || "بدون توضیح";
    try {
      if (cmd === "/warn") {
        await env.DB.prepare("INSERT INTO warnings(chat_id,user_id,admin_id,reason) VALUES(?,?,?,?)")
          .bind(msg.chat.id, target.id, msg.from.id, reason).run();
        const row = await env.DB.prepare("SELECT COUNT(*) n FROM warnings WHERE chat_id=? AND user_id=?").bind(msg.chat.id, target.id).first();
        return answer(env, msg.chat.id, `⚠️ به ${mention(target)} اخطار داده شد. تعداد اخطارها: ${row.n}`, { reply_to_message_id: msg.message_id });
      }
      if (cmd === "/mute") {
        await tg(env, "restrictChatMember", { chat_id: msg.chat.id, user_id: target.id, permissions: { can_send_messages: false }, until_date: Math.floor(Date.now()/1000) + 600 });
        return answer(env, msg.chat.id, `🔇 ${mention(target)} برای ۱۰ دقیقه محدود شد.`, { reply_to_message_id: msg.message_id });
      }
      if (cmd === "/ban") {
        await tg(env, "banChatMember", { chat_id: msg.chat.id, user_id: target.id });
        return answer(env, msg.chat.id, `⛔ ${mention(target)} مسدود شد.`, { reply_to_message_id: msg.message_id });
      }
      await tg(env, "unbanChatMember", { chat_id: msg.chat.id, user_id: target.id, only_if_banned: true });
      return answer(env, msg.chat.id, `✅ محدودیت بن ${mention(target)} برداشته شد.`, { reply_to_message_id: msg.message_id });
    } catch (e) {
      return answer(env, msg.chat.id, `عملیات ناموفق بود: ${esc(e.message)}`, { reply_to_message_id: msg.message_id });
    }
  }

  if (env.WELCOME_ENABLED !== "false" && msg.new_chat_members?.length) {
    for (const user of msg.new_chat_members) if (!user.is_bot)
      await answer(env, msg.chat.id, `خوش آمدی ${mention(user)} 🌷\nلطفاً قوانین گروه را رعایت کن.`);
  }

  if (await isAdmin(env, msg.chat.id, msg.from.id)) return;
  const blocked = (env.BLOCKED_WORDS || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean);
  let reason = null;
  if (env.ANTI_LINK !== "false" && /(https?:\/\/|www\.|t\.me\/|telegram\.me\/)/i.test(text)) reason = "لینک غیرمجاز";
  else if (blocked.some(w => text.toLowerCase().includes(w))) reason = "استفاده از کلمه ممنوع";

  if (!reason && env.ANTI_FLOOD !== "false") {
    const now = Math.floor(Date.now()/1000), windowSec = Number(env.FLOOD_WINDOW_SECONDS || 8);
    const max = Number(env.FLOOD_MAX_MESSAGES || 5);
    await env.DB.prepare("DELETE FROM flood_events WHERE created_at < ?").bind(now - windowSec).run();
    await env.DB.prepare("INSERT INTO flood_events(chat_id,user_id,created_at) VALUES(?,?,?)").bind(msg.chat.id, msg.from.id, now).run();
    const count = await env.DB.prepare("SELECT COUNT(*) n FROM flood_events WHERE chat_id=? AND user_id=? AND created_at>=?")
      .bind(msg.chat.id, msg.from.id, now-windowSec).first();
    if (count.n > max) reason = "ارسال پیام‌های بیش از حد";
  }
  if (reason) {
    try {
      await tg(env, "deleteMessage", { chat_id: msg.chat.id, message_id: msg.message_id });
      await logEvent(env, msg.chat.id, msg.from.id, "message_removed", reason);
      await answer(env, msg.chat.id, `⚠️ پیام ${mention(msg.from)} حذف شد: ${reason}`);
    } catch { /* Bot may lack delete-message permission. */ }
  }
}
async function processUpdate(env, upd) {
  if (upd.callback_query) return handleCallback(env, upd.callback_query);
  if (upd.my_chat_member || upd.chat_member) return handleMemberUpdate(env, upd);
  const msg = upd.message;
  if (!msg) return;
  if (msg.chat.type === "private" && msg.text?.startsWith("/start")) return ownerStart(env, msg);
  if (isGroup(msg.chat)) return handleGroupMessage(env, msg);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") return Response.json({ ok: true, service: "telegram-growth-manager-worker" });
    if (url.pathname === "/setup" && request.method === "GET") {
      if (!env.SETUP_SECRET || url.searchParams.get("key") !== env.SETUP_SECRET)
        return new Response("Unauthorized", { status: 401 });
      const webhookUrl = `${url.origin}/telegram`;
      const result = await tg(env, "setWebhook", {
        url: webhookUrl,
        secret_token: env.WEBHOOK_SECRET,
        allowed_updates: ["message", "callback_query", "my_chat_member", "chat_member"],
        drop_pending_updates: false,
      });
      return Response.json({ ok: true, webhook: webhookUrl, telegram: result });
    }
    if (url.pathname !== "/telegram" || request.method !== "POST") return new Response("Not found", { status: 404 });
    if (env.WEBHOOK_SECRET && request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET)
      return new Response("Forbidden", { status: 403 });
    let update;
    try { update = await request.json(); } catch { return new Response("Bad Request", { status: 400 }); }
    try {
      await processUpdate(env, update);
      return new Response("OK");
    } catch (e) {
      console.error("Update processing error:", e?.stack || e);
      return new Response("Internal error", { status: 500 });
    }
  },
};
