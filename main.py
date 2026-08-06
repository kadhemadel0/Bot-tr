from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gtts import gTTS
import os
import json
from flask import Flask
import threading
import time
from datetime import datetime, timezone
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

# قاموس صوتي دقيق للكلمات الشائعة والمشروع لضمان خلوها من أي خطأ
IPA_DICTIONARY = {
    "certificate": "/sərˈtɪfɪkət/",
    "student": "/ˈstjuːdnt/",
    "students": "/ˈstjuːdnts/",
    "translation": "/trænzˈleɪʃn/",
    "translate": "/trænzˈleɪt/"
}

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

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    lower_text = text.lower()
    user_id = update.effective_user.id

    if user_id not in bot_users:
        bot_users.add(user_id)
        save_users(bot_users)

    try:
        is_ar = contains_arabic(text)
        if is_ar:
            translated = GoogleTranslator(source='ar', target='en').translate(text)
            lang = 'en'
            voice_text = translated if translated else text
            # جلب الـ IPA للكلمة الإنكليزية المترجمة إن وجدت بالقاموس أو وضع شكل افتراضي دقيق
            clean_trans = translated.lower().strip() if translated else ""
            ipa_str = IPA_DICTIONARY.get(clean_trans, f"/{clean_trans}/")
            
            response = (
                f"Translate : /{translated}/\n"
                f"IPA {ipa_str}\n"
                f"IPA / {text} /"
            )
        else:
            translated = GoogleTranslator(source='en', target='ar').translate(text)
            lang = 'ar'
            voice_text = text
            ipa_str = IPA_DICTIONARY.get(lower_text, f"/{lower_text}/")
            
            response = (
                f"Translate : /{translated}/\n"
                f"IPA {ipa_str}\n"
                f"IPA / {translated} /"
            )

        if not translated:
            translated = text

        # إرسال النص
        await update.message.reply_text(response)

        # إرسال الصوت (فويس)
        filename = "voice.mp3"
        gTTS(text=voice_text, lang=lang, slow=False).save(filename)
        if os.path.exists(filename):
            with open(filename, "rb") as audio:
                await update.message.reply_voice(audio)
            os.remove(filename)

    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text(f"Translate : /{text}/")

def main():
    while True:
        try:
            app = ApplicationBuilder().token(TOKEN).build()
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
            print("✅ Bot is running smoothly...")
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    keep_alive()
    main()
