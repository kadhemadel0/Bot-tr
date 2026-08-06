from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from gtts import gTTS
import os
import json
from flask import Flask
import threading
import time
from deep_translator import GoogleTranslator

# --- إعدادات سيرفر الـ Flask لإبقاء البوت شغال على Render ---
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "I am alive"

def run():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = threading.Thread(target=run)
    t.start()
# --------------------------------------------------------

TOKEN = "8834292206:AAGIbtd57w50NPozFUQsGHKGxQ4b_BT99PY"
ADMIN_ID = 7964624188
USERS_FILE = "users.json"
BOT_USERNAME = "@Xkadhem"

# --- دوال حفظ وإدارة المستخدمين ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_users(users_set):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users_set), f)

bot_users = load_users()


def contains_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    is_new = user_id not in bot_users
    
    if is_new:
        bot_users.add(user_id)
        save_users(bot_users)
        
        if user_id != ADMIN_ID:
            username_str = f"@{user.username}" if user.username else "لا يوجد يوزر"
            admin_notification = f"🚨 شخص جديد دخل للبوت!\n\n👤 الاسم: {user.full_name}\n🔗 اليوزر: {username_str}\n🆔 الأيدي: `{user_id}`\n📊 العدد الكلي: {len(bot_users)}"
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notification, parse_mode="Markdown")
            except Exception as e:
                print(f"Error sending admin notification: {e}")

    await update.message.reply_text(f"أهلاً بك في بوت الترجمة السريع! 🚀\nأرسل أي كلمة أو جملة وسأقوم بترجمتها لك.\nللنطق اكتب: انطقي [الكلمة]\nللصوتي الصوتي: اعطيني IPA [الكلمة]")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"📊 عدد المستخدمين الحاليين للبوت: {len(bot_users)} شخص.")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    lower_text = text.lower()

    try:
        # 1. حالة طلب النطق (انطقي ...)
        if lower_text.startswith("انطقي "):
            target_word = text[6:].strip()
            if not target_word:
                await update.message.reply_text("يرجى كتابة الكلمة بعد كلمة انطقي.")
                return
            
            filename = "voice.mp3"
            try:
                # تحديد لغة النطق حسب الحروف (عربي أو إنجليزي)
                lang = "ar" if contains_arabic(target_word) else "en"
                gTTS(text=target_word, lang=lang, slow=False).save(filename)
                if os.path.exists(filename):
                    with open(filename, "rb") as audio:
                        await update.message.reply_voice(audio)
                    os.remove(filename)
            except Exception as e:
                if os.path.exists(filename):
                    os.remove(filename)
                await update.message.reply_text("عذراً، حدث خطأ أثناء توليد الصوت.")
            return

        # 2. حالة طلب الـ IPA (اعطيني IPA ...)
        if lower_text.startswith("اعطيني ipa "):
            target_word = text[12:].strip()
            if not target_word:
                await update.message.reply_text("يرجى كتابة الكلمة المطلوبة.")
                return
            # تزويد المستخدم برمز تقريبي أو تنبيه جاهز للـ IPA
            await update.message.reply_text(f"الرسم الصوتي (IPA) للكلمة ({target_word}):\n/[قريباً يتم ربطه بقاموس صوتي أو عرض النص]/")
            return

        # 3. الحالة العادية: ترجمة مباشرة لأي كلمة تُرسل
        is_ar = contains_arabic(text)
        if is_ar:
            translated = GoogleTranslator(source='ar', target='en').translate(text)
        else:
            translated = GoogleTranslator(source='en', target='ar').translate(text)

        if not translated:
            translated = "not found"

        response = f"الترجمة: {translated}"
        await update.message.reply_text(response)

    except Exception as e:
        print(f"Error occurred: {e}")
        await update.message.reply_text("not found")


def main():
    while True:
        try:
            app = ApplicationBuilder().token(TOKEN).build()

            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("stats", stats_command))

            app.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle
                )
            )

            print("✅ Bot is running smoothly without AI core...")
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}. Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    keep_alive()
    main()
