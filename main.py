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
from PIL import Image
import pytesseract

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
- Voice Pronunciation (English only)
- Image Text Translation (OCR)
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
        if word[0].isupper():
            continue
            
        new = spell.correction(word)
        if new and new.lower() != word.lower():
            corrected = corrected.replace(word, new, 1)
            changed = True

    return corrected, changed


# دالة موحدة لمعالجة النصوص (سواء أرسلها المستخدم كتابةً أو تم استخراجها من صورة)
async def process_translation(update: Update, text: str, is_from_image: bool = False):
    text = text.strip()
    if not text:
        await update.message.reply_text("not found")
        return

    is_arabic = contains_arabic(text)

    try:
        if not is_arabic:
            corrected, changed = correct_spelling(text)

            if corrected != text and not is_from_image:
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

            if not translated or translated.strip() == "":
                translated = "not found"

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
            # الكلمات الإنجليزية: توليد وإرسال ملف الصوت (Voice)
            filename = "voice.mp3"
            try:
                gTTS(
                    text=text,
                    lang="en",
                    slow=False
                ).save(filename)
            except Exception:
                filename = None

            await update.message.reply_text(response)

            if filename and os.path.exists(filename):
                with open(filename, "rb") as audio:
                    await update.message.reply_voice(audio)
                os.remove(filename)

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

            if not translated or translated.strip() == "" or translated.lower() == text.lower():
                translated = "not found"
            
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
            # الكلمات العربية: إرسال النص والترجمة والـ IPA فقط (بدون فويس نهائياً)
            await update.message.reply_text(response)

    except Exception as e:
        print(f"Error occurred: {e}")
        await update.message.reply_text("not found")


# معالج النصوص العادية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await process_translation(update, text, is_from_image=False)


# معالج الصور الجديد (OCR)
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        image_path = "downloaded_image.jpg"
        await file.download_to_drive(image_path)
        
        extracted_text = pytesseract.image_to_string(Image.open(image_path))
        
        if os.path.exists(image_path):
            os.remove(image_path)
            
        cleaned_text = extracted_text.strip()
        
        if not cleaned_text:
            await update.message.reply_text("❌ لم يتم العثور على نص واضح داخل الصورة.")
            return
            
        await update.message.reply_text(f"📷 النص المستخرج من الصورة:\n`{cleaned_text}`", parse_mode="Markdown")
        
        # معالجة النص المستخرج مثل الكلمة الإنجليزية تماماً
        await process_translation(update, cleaned_text, is_from_image=True)
        
    except Exception as e:
        print(f"Image error: {e}")
        await update.message.reply_text("حدث خطأ أثناء قراءة الصورة.")


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
            handle_text
        )
    )

    # معالج الصور الجديد
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_image
        )
    )

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    keep_alive()
    main()
