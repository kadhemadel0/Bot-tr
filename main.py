from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from deep_translator import GoogleTranslator
from gtts import gTTS
import eng_to_ipa as ipa
import os
import json
import re
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


# --- دالة ترجمة آمنة مع نظام إعادة المحاولة التلقائي (Retry) لمنع التعليق ---
def safe_translate(text, source_lang, target_lang):
    for _ in range(3):  # يحاول 3 مرات في حال حدوث تعليق أو تايم أوت
        try:
            translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
            if translated:
                return translated
        except:
            time.sleep(0.5)
    return "not found"


# --- دالة تحويل رموز الـ IPA إلى لفظ عربي جذري وشامل لكل الكلمات ---
def ipa_to_arabic_phonetic(word, ipa_text):
    if not ipa_text or ipa_text == "IPA not found":
        return "غير متوفر"
    
    # تنظيف الرموز الصوتية
    phonetic = ipa_text.strip('/')
    phonetic = phonetic.replace("ˈ", "").replace("ˌ", "").replace(".", "")
    
    # خريطة التحويل الشاملة لجميع الأصوات والحركات
    ipa_mapping = {
        'iː': 'ِي', 'uː': 'ُو', 'ɑː': 'َا', 'ɔː': 'و', 'ɜː': 'ر',
        'eɪ': 'ِيْ', 'aɪ': 'َايْ', 'ɔɪ': 'ُويْ', 'aʊ': 'َاوْ', 'əʊ': 'ُو',
        'ɪə': 'ِيَة', 'eə': 'ِيْر', 'ʊə': 'ُوَة',
        'tʃ': 'تش', 'dʒ': 'ج', 'ŋ': 'نْغ',
        'ɪ': 'ِ', 'i': 'ِ', 'æ': 'َ', 'ɒ': 'َ', 'ʊ': 'ُ',
        'u': 'و', 'ʌ': 'َ', 'ə': 'َ', 'e': 'ي',
        'ɑ': 'َا', 'a': 'َا',
        'p': 'ب', 'b': 'ب', 't': 'ت', 'd': 'د',
        'k': 'ك', 'g': 'گ', 'f': 'ف', 'v': 'ڤ',
        'θ': 'ث', 'ð': 'ذ', 's': 'س', 'z': 'ز',
        'ʃ': 'ش', 'ʒ': 'ج', 'h': 'ه', 'm': 'م',
        'n': 'ن', 'l': 'ل', 'r': 'ر', 'j': 'ي', 'w': 'و',
        'ɡ': 'گ', 'ː': ''
    }
    
    sorted_keys = sorted(ipa_mapping.keys(), key=len, reverse=True)
    for key in sorted_keys:
        phonetic = phonetic.replace(key, ipa_mapping[key])
        
    # خطوة احترازية جذرية: إزالة أي حروف إنجليزية قد تبقى لضمان نظافة الناتج تماماً
    phonetic = re.sub(r'[a-zA-Z]', '', phonetic)
    
    return phonetic.strip()


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


def contains_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    is_arabic = contains_arabic(text)

    try:
        if not is_arabic:
            target_word = text
            translated = safe_translate(target_word, "en", "ar")

            try:
                ipa_en = ipa.convert(target_word)
                if not ipa_en or "?" in ipa_en:
                    ipa_en = "IPA not found"
            except:
                ipa_en = "IPA not found"

            arabic_phonetic = ipa_to_arabic_phonetic(target_word, ipa_en)
            voice_text = target_word

        else:
            translated = safe_translate(text, "ar", "en")
            target_word = translated if translated != "not found" else text

            try:
                ipa_en = ipa.convert(target_word) if translated != "not found" else "IPA not found"
                if not ipa_en or "?" in ipa_en:
                    ipa_en = "IPA not found"
            except:
                ipa_en = "IPA not found"

            arabic_phonetic = ipa_to_arabic_phonetic(target_word, ipa_en) if translated != "not found" else "غير متوفر"
            voice_text = target_word if translated != "not found" else None

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

            print("✅ Bot is running smoothly...")
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}. Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    keep_alive()
    main()
