import re
import requests
from urllib.parse import urlsplit
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

# ضع توكن البوت هنا من BotFather
BOT_TOKEN = "8733112337:AAGLcvft_GpLtnwRE0LnufQnS4io4L4nJOA"

# أسعار تقريبية بالدولار: تسجيل أول سنة / التجديد السنوي
PRICES = {
    "com": ("9-16$", "14-22$"),
    "net": ("11-18$", "16-24$"),
    "org": ("7-15$", "14-22$"),
    "co": ("20-35$", "25-40$"),
    "io": ("25-45$", "35-60$"),
    "store": ("2-15$", "30-60$"),
    "shop": ("3-20$", "25-50$"),
    "online": ("2-15$", "30-55$"),
    "site": ("2-12$", "25-45$"),
    "app": ("12-25$", "18-30$"),
    "info": ("3-12$", "20-35$"),
    "me": ("8-20$", "15-30$"),
    "xyz": ("1-5$", "10-20$"),
    "dev": ("10-18$", "15-25$"),
    "ai": ("50-90$", "60-100$"),
    "tech": ("5-20$", "35-60$"),
    "com": ("9-16$", "14-22$")
}

def check_domain(domain):
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].split("?")[0].split("#")[0]
    domain = domain.rstrip(".")

    try:
        domain = domain.encode("idna").decode("ascii")
    except Exception:
        return None, "اسم الدومين غير صالح"

    if len(domain) > 253 or "." not in domain:
        return None, "أرسل دوميناً كاملاً مثل example.com"

    labels = domain.split(".")
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x) for x in labels):
        return None, "صيغة الدومين غير صحيحة"

    try:
        response = requests.get(
            "https://rdap.org/domain/" + domain,
            timeout=15,
            headers={"User-Agent": "DomainCheckerBot/1.0"}
        )

        if response.status_code == 200:
            status = "محجوز بالفعل ❌"
        elif response.status_code == 404:
            status = "يبدو أنه متاح للتسجيل ✅"
        else:
            return None, f"تعذر التأكد من التوفر (HTTP {response.status_code})"

        return domain, status

    except requests.RequestException:
        return None, "تعذر الاتصال بخدمة فحص الدومينات. حاول لاحقاً."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 أهلاً بك في بوت فحص الدومينات\n\n"
        "أرسل اسم الدومين الذي تريد فحصه:\n"
        "مثال:\n"
        "original-store.com\n\n"
        "سأفحص التوفر وأعرض الأسعار التقديرية."
    )

async def handle_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()

    await update.message.reply_text("🔎 جارٍ فحص الدومين...")

    domain, result = await __import__("asyncio").to_thread(check_domain, raw)

    if not domain:
        await update.message.reply_text("⚠️ " + result)
        return

    extension = domain.rsplit(".", 1)[-1]
    first, renewal = PRICES.get(extension, ("10-30$", "15-40$"))

    message = (
        "🌐 تقرير فحص الدومين\n"
        "━━━━━━━━━━━━━━\n"
        f"🔹 الدومين: {domain}\n"
        f"📌 الحالة: {result}\n"
        "━━━━━━━━━━━━━━\n"
        f"💰 سعر التسجيل التقريبي: {first}\n"
        f"🔄 التجديد السنوي التقريبي: {renewal}\n"
        "💵 العملة: الدولار الأمريكي\n"
        "━━━━━━━━━━━━━━\n"
        "⚠️ الأسعار تقديرية وليست عروض أسعار مباشرة.\n"
        "تحقق من السعر النهائي لدى شركة التسجيل قبل الشراء."
    )

    await update.message.reply_text(message)

def main():
    if BOT_TOKEN == "8733112337:AAGLcvft_GpLtnwRE0LnufQnS4io4L4nJOA":
        print("ضع توكن البوت في ملف domain_bot.py أولاً")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_domain))

    print("Domain Checker Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
