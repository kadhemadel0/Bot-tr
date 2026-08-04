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
from flask import Flask
import threading

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

spell = SpellChecker(language="en")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
Welcome to the Translation Bot

Features:
- English ↔ Arabic Translation
- IPA (Phonetic Transcription)
- Voice Pronunciation
- Spelling Correction

Dev: @Xkadhem
"""
    await update.message.reply_text(text.strip())


def contains_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)


def correct_spelling(sentence):
    words = re.findall(r"[A-Za-z']+", sentence)
    corrected = sentence
    changed = False

    for word in words:
        # إذا الكلمة تبدأ بحرف كبير (مثل الأسماء Ali, Ahmed)، نتخلى عنها وما نغيرها أبداً
        if word[0].isupper():
            continue
            
        new = spell.correction(word)
        if new and new.lower() != word.lower():
            corrected = corrected.replace(word, new, 1)
            changed = True

    return corrected, changed


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                translated = GoogleTranslator(
                    source="en",
                    target="ar"
                ).translate(text)
            except TranslationNotFound:
                translated = "not found"
            except Exception:
                translated = "not found"

            # إذا الترجمة طلعت فارغة أو متشابهة بطريقة غريبة
            if not translated or translated.strip() == "":
                translated = "not found"

            voice_text = text
            
            try:
                ipa_text = ipa.convert(text)
                if ipa_text.strip() == "" or "?" in ipa_text:
                    ipa_text = "IPA not found"
            except Exception:
                ipa_text = "IPA not found"

            response = f""" الترجمة:{translated}
(IPA):/{ipa_text}/

النطق الأصلي:{text}
"""
        else:
            try:
                translated = GoogleTranslator(
                    source="ar",
                    target="en"
                ).translate(text)
            except TranslationNotFound:
                translated = "not found"
            except Exception:
                translated = "not found"

            # التحقق إذا الكلمة العربية خطأ أو مو مفهومة
            if not translated or translated.strip() == "" or translated.lower() == text.lower():
                translated = "not found"

            voice_text = translated
            
            try:
                ipa_text = ipa.convert(translated)
                if ipa_text.strip() == "" or "?" in ipa_text or translated == "not found":
                    ipa_text = "IPA not found"
            except Exception:
                ipa_text = "IPA not found"

            response = f"""
            الترجمه : {translated}

(IPA): /{ipa_text}/
النص الأصلي :{text}

"""

        filename = "voice.mp3"

        # لا تولد صوت إذا الكلمة غير موجودة أو خطأ
        if voice_text and voice_text != "not found":
            try:
                gTTS(
                    text=voice_text,
                    lang="en",
                    slow=False
                ).save(filename)
            except Exception:
                filename = None
        else:
            filename = None

        await update.message.reply_text(response)

        if filename and os.path.exists(filename):
            with open(filename, "rb") as audio:
                await update.message.reply_voice(audio)
            os.remove(filename)

    except Exception as e:
        print(f"Error occurred: {e}")
        await update.message.reply_text("not found")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle
        )
    )

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    keep_alive()
    main()
