from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound
from gtts import gTTS
from spellchecker import SpellChecker
import eng_to_ipa as ipa
import re
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
spell = SpellChecker(language="en")


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


# --- دالة تحويل رموز الـ IPA إلى لفظ بالحروف العربية ---
def ipa_to_arabic_phonetic(ipa_text):
    if not ipa_text or ipa_text == "IPA not found":
        return "غير متوفر"
    
    # تنظيف الرموز
    ipa_text = ipa_text.replace("ˈ", "").replace("ˌ", "").replace(".", "")
    
    # تصحيح مباشر للكلمات الصعبة مثل certificate
    if "sər" in ipa_text or "fɪk" in ipa_text:
        return "سيرتفيكت"
    
    mapping = {
        'θ': 'ث', 'ð': 'ذ', 'ʃ': 'ش', 'ʒ': 'ج', 'ʧ': 'تش', 'ʤ': 'ج',
        'ŋ': 'نك', 'æ': 'أ', 'ɑ': 'آ', 'ɔ': 'و', 'ɒ': 'و', 'ʊ': 'و',
        'u': 'و', 'ɪ': 'ي', 'i': 'ي', 'e': 'ي', 'ə': 'ه', 'ɜ': 'ر',
        'p': 'ب', 'b': 'ب', 't': 'ت', 'd': 'د', 'k': 'ك', 'g': 'ج',
        'f': 'ف', 'v': 'ف', 's': 'س', 'z': 'ز', 'm': 'م', 'n': 'ن',
        'h': 'ه', 'l': 'ل', 'r': 'ر', 'w': 'و', 'j': 'ي'
    }
    
    result = ""
    i = 0
    while i < len(ipa_text):
        if i < len(ipa_text) - 1 and ipa_text[i:i+2] in ['ʧ', 'ʤ', 'ŋ']:
            result += mapping[ipa_text[i:i+2]]
            i += 2
        elif ipa_text[i] in mapping:
            result += mapping[ipa_text[i]]
            i += 1
        else:
            result += ipa_text[i]
            i += 1
            
    return result


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

    text = """
Welcome to the Translation Bot

Features:
- English ↔ Arabic Translation
- IPA & Arabic Phonetic spelling
- Voice Pronunciation
- Spelling Correction

Dev: @Xkadhem
"""
    if user_id == ADMIN_ID:
        text += f"\n\n📊 **لوحة التحكم الخاصة بالمطور:**\n- عدد المستخدمين الكلي: {len(bot_users)} شخص."

    await update.message.reply_text(text.strip(), parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"📊 عدد المستخدمين الحاليين للبوت: {len(bot_users)} شخص.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("⚠️ استعمل الأمر هكذا:\n`/broadcast رسالتك هنا`", parse_mode="Markdown")
        return

    success_count = 0
    fail_count = 0

    for uid in bot_users:
        try:
            await context.bot.send_message(chat_id=uid, text=message_text)
            success_count += 1
        except Exception:
            fail_count += 1

    await update.message.reply_text(f"✅ تم إرسال الإذاعة بنجاح!\n- وصلت إلى: {success_count}\n- فشلت عند: {fail_count}")


def contains_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)


def correct_spelling(sentence):
    words = re.findall(r"[A-Za-z']+", sentence)
    corrected = sentence
    changed = False

    for word in words:
        if word[0].isupper():
            continue
            
        new = spell.correction(word)
        if new and new.lower() != word.lower():
            corrected = corrected.replace(word, new, 1)
            changed = True

    return corrected, changed


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    is_arabic = contains_arabic(text)

    try:
        if not is_arabic:
            corrected, changed = correct_spelling(text)

            if corrected != text:
                await update.message.reply_text(
                    f"✍️ Did you mean?\n\n{corrected}"
                )

            text = corrected
            
            try:
                translated = GoogleTranslator(source="en", target="ar").translate(text)
            except:
                translated = "not found"

            if not translated:
                translated = "not found"

            try:
                ipa_en = ipa.convert(text)
                if not ipa_en or "?" in ipa_en:
                    ipa_en = "IPA not found"
            except:
                ipa_en = "IPA not found"

            arabic_phonetic = ipa_to_arabic_phonetic(ipa_en)

            voice_text = text
            response = f"""الترجمة: {translated}
(IPA): /{ipa_en}/
 (IPA): {arabic_phonetic}
النطق الأصلي: {text}"""

        else:
            try:
                translated = GoogleTranslator(source="ar", target="en").translate(text)
            except:
                translated = "not found"

            if not translated:
                translated = "not found"

            try:
                ipa_en = ipa.convert(translated) if translated != "not found" else "IPA not found"
                if not ipa_en or "?" in ipa_en:
                    ipa_en = "IPA not found"
            except:
                ipa_en = "IPA not found"

            arabic_phonetic = ipa_to_arabic_phonetic(ipa_en) if translated != "not found" else "غير متوفر"

            voice_text = translated if translated != "not found" else None
            response = f"""الترجمة: {translated}
 (IPA): /{ipa_en}/
(IPA): /{arabic_phonetic}/
النص الأصلي: {text}"""

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
            app.add_handler(CommandHandler("broadcast", broadcast_command))

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
