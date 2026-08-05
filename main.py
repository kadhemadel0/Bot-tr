from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai
from gtts import gTTS
import os
import json
from flask import Flask
import threading
import time

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

# إعداد عميل الذكاء الاصطناعي (تأكد أن مفتاح الـ API مخزن في متغيرات البيئة بـ Render باسم GEMINI_API_KEY)
ai_client = genai.Client()


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


# --- دالة الذكاء الاصطناعي الاحترافية للترجمة والتحليل الصوتي الدقيق ---
def get_linguistic_analysis(text):
    prompt = f"""
    Analyze the following text/word: "{text}"
    Provide the response strictly in a JSON format with three keys:
    1. "translation": If the input is in English, provide its accurate Arabic translation. If it is in Arabic, provide its accurate English translation.
    2. "ipa": The precise International Phonetic Alphabet (IPA) representation for the English word/translation (enclosed in slashes or clean).
    3. "phonetic_arabic": A high-quality, professional Arabic phonetic transcription (with correct Arabic diacritics/tashkeel) showing an Iraqi/standard Arabic speaker how to pronounce the English term natively and accurately, without any English letters remaining.
    """
    
    for _ in range(3):  # نظام إعادة محاولة تلقائي لمنع أي تعليق
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
            )
            
            # تنظيف النص واستخراج الـ JSON بدقة لتجنب أخطاء التنسيق
            res_text = response.text.strip()
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(res_text)
            return {
                "translation": data.get("translation", "not found"),
                "ipa": data.get("ipa", "IPA not found"),
                "phonetic_arabic": data.get("phonetic_arabic", "غير متوفر")
            }
        except Exception as e:
            print(f"AI parsing error: {e}")
            time.sleep(0.5)
            
    return {"translation": "not found", "ipa": "IPA not found", "phonetic_arabic": "غير متوفر"}


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

    await update.message.reply_text(BOT_USERNAME)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"📊 عدد المستخدمين الحاليين للبوت: {len(bot_users)} شخص.")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    is_arabic = contains_arabic(text)

    try:
        # استدعاء التحليل اللغوي الذكي والشامل بجودة عالية جداً
        analysis = get_linguistic_analysis(text)
        
        translated = analysis["translation"]
        ipa_en = analysis["ipa"]
        arabic_phonetic = analysis["phonetic_arabic"]

        # تحديد الكلمة الإنجليزية المناسبة لقراءة الصوت (gTTS)
        if not is_arabic:
            voice_text = text
        else:
            voice_text = translated if translated != "not found" else None

        response = f"الترجمة: {translated}\nIPA: /{ipa_en}/\nاللفظ العربي: {arabic_phonetic}"
        await update.message.reply_text(response)

        filename = "voice.mp3"
        if voice_text and voice_text != "not found":
            try:
                gTTS(text=voice_text, lang="en", slow=False).save(filename)
                if os.path.exists(filename):
                    with open(filename, "rb") as audio:
                        await update.message.reply_voice(audio)
                    os.remove(filename)
            except:
                if os.path.exists(filename):
                    os.remove(filename)

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

            print("✅ Bot is running smoothly with AI core...")
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}. Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    keep_alive()
    main()
