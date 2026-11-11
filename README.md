# Telegram Growth Manager — Cloudflare Workers

نسخه سازگار با Cloudflare Workers؛ معماری از Aiogram/Long Polling به JavaScript Worker + Telegram Webhook + Cloudflare D1 تبدیل شده است.

## امکانات پیاده‌سازی‌شده
- پنل خصوصی مالک با `/start` و کنترل دسترسی با `OWNER_ID`
- ثبت خودکار گروه‌ها/کانال‌ها با رویداد `my_chat_member`
- فهرست گروه‌ها و کانال‌های متصل
- ساخت لینک دعوت اختصاصی برای گروه‌ها
- آمار گروه‌های متصل، اعضای ثبت‌شده و اخطارها
- خوشامدگویی به اعضای جدید (وقتی پیام ورود برای بات ارسال شود)
- ضدلینک، ضدفلود و فیلتر کلمات ممنوعه
- دستورهای `/warn`، `/mute` (۱۰ دقیقه)، `/ban` و `/unban` در پاسخ به پیام عضو
- ثبت ورود/خروج اعضا از رویداد `chat_member`
- انتشار خودکار محتوای معرفی بازارک در کانال و گروه با Cloudflare Cron
- کانال: هر ۸ ساعت (حداکثر ۳ پست در روز)؛ گروه: هر ۲۴ ساعت (۱ پست در روز)
- چرخش متن‌های تبلیغاتی و ثبت موفقیت/خطای هر انتشار در D1

## پیش‌نیازها
- حساب Cloudflare و Wrangler 4
- Bot Token جدید از BotFather
- شناسه عددی مالک تلگرام
- یک پایگاه داده Cloudflare D1

## نصب و Deploy

### 1. ایجاد D1
```bash
npm install
npx wrangler d1 create telegram-growth-manager-db
```
شناسه‌ای که Cloudflare برمی‌گرداند را در `wrangler.toml` جایگزین `REPLACE_WITH_D1_DATABASE_ID` کن.

### 2. ساخت جدول‌ها
```bash
npx wrangler d1 execute telegram-growth-manager-db --remote --file=./schema.sql
```

### 3. افزودن Secrets
مقادیر را در ترمینال وارد کن؛ هیچ توکنی را در چت یا GitHub قرار نده:
```bash
npx wrangler secret put BOT_TOKEN
npx wrangler secret put OWNER_ID
npx wrangler secret put WEBHOOK_SECRET
npx wrangler secret put SETUP_SECRET
```
برای `WEBHOOK_SECRET` و `SETUP_SECRET` دو رشته تصادفی طولانی جداگانه استفاده کن. مقدار OWNER_ID فقط عدد شناسه تلگرام مالک است.

### 4. انتشار
```bash
npx wrangler deploy
```
آدرس Worker را از خروجی بگیر، سپس این نشانی را در مرورگر باز کن:
```text
https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/setup?key=YOUR_SETUP_SECRET
```
اگر همه‌چیز درست باشد، پاسخ `{"ok":true,...}` دریافت می‌کنی و Webhook ثبت می‌شود. مقدار کلید را محرمانه نگه دار. بعد از ثبت Webhook، می‌توانی مقدار SETUP_SECRET را عوض کنی یا آن را حذف کنی.

### 5. بررسی
```text
https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/health
```
باید `ok: true` نشان دهد. سپس به ربات در تلگرام `/start` بفرست.

## سیستم رشد خودکار ۲۴ ساعته

در `schema.sql` دو مقصد فعلی از قبل درج شده‌اند:
- `@MyBazarek` به‌عنوان کانال، هر ۸ ساعت
- `@mybazarek2026` به‌عنوان گروه، هر ۲۴ ساعت

اگر نقش این دو لینک برعکس است، مقدار `target_type` را در جدول `growth_targets` اصلاح کن. اجرای Cron هر ۸ ساعت است؛ اولین انتشار در اجرای بعدی Cron انجام می‌شود. برای فعال‌ماندن انتشار، Worker باید Deploy شده و Cron در تنظیمات پروژه فعال باشد. ربات در کانال باید دسترسی Post Messages و در گروه دسترسی Send Messages داشته باشد.

پس از اجرای migration، در پنل خصوصی ربات `/start` بزن و گزینه «رشد خودکار ۲۴ ساعته» را برای دیدن وضعیت و تعداد انتشارها باز کن. برای تغییر تعداد دفعات، ستون `interval_hours` در جدول `growth_targets` را تغییر بده. برای توقف یک مقصد، `enabled=0` قرار بده.

این سیستم پیام‌های معرفی خود ربات را در مقصدهای خودت منتشر می‌کند؛ به افراد ناشناس پیام نمی‌دهد، عضو فیک تولید نمی‌کند و تضمین تعداد مشخصی بازدید/عضو ندارد. رشد واقعی به کیفیت محتوا، مخاطب و اشتراک‌گذاری کاربران بستگی دارد.

## تنظیمات تلگرام
1. ربات را به گروه اضافه کن و مدیر بساز.
2. برای فیلتر پیام‌ها دسترسی حذف پیام، و برای mute/ban دسترسی محدودکردن/مسدودکردن اعضا بده.
3. برای لینک دعوت دسترسی دعوت اعضا بده.
4. در BotFather با `/setprivacy` حالت Privacy را خاموش کن و سپس بات را از گروه حذف و دوباره اضافه کن تا پیام‌های معمولی را برای ضدلینک/ضدفلود ببیند.
5. برای ثبت رویدادهای ورود/خروج، بات باید مدیر گروه باشد و رویدادهای `chat_member` به آن برسند.

## متغیرهای قابل تنظیم
در بخش `[vars]` فایل `wrangler.toml`:
- `ANTI_LINK`: `true` یا `false`
- `ANTI_FLOOD`: `true` یا `false`
- `FLOOD_MAX_MESSAGES`: حداکثر پیام در بازه
- `FLOOD_WINDOW_SECONDS`: بازه زمانی
- `BLOCKED_WORDS`: کلمات ممنوع، جداشده با کاما
- `WELCOME_ENABLED`: کنترل خوشامدگویی
- Cron: هر ۸ ساعت از بخش `[triggers]` در `wrangler.toml`

## نکات و محدودیت‌ها
- این نسخه، قابلیت‌های موجود MVP قبلی را به Worker منتقل می‌کند؛ داشبورد وب، زمان‌بندی پست‌ها، کمپین تبلیغاتی پیشرفته، سیستم امتیاز/مسابقه و AI moderation هنوز پیاده‌سازی نشده‌اند.
- `WELCOME_ENABLED` در این نسخه فعلاً همیشه فعال است و در نسخه بعدی به شرط تنظیمات وصل می‌شود.
- آمار اعضا از رویدادهایی محاسبه می‌شود که بعد از نصب و با مجوزهای مناسب دریافت شده‌اند؛ شمار کل واقعی اعضا نیست.
- Cloudflare Workers برای این نسخه نیازمند D1 است؛ SQLite فایل محلی قبلی در محیط Worker قابل استفاده نیست.
- توکن افشاشده قبلی را دوباره استفاده نکن؛ در BotFather آن را revoke کرده و فقط توکن جدید را به عنوان Secret ثبت کن.
