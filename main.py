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
from spellchecker import SpellChecker
import eng_to_ipa as ipa
import requests
import re
import os

TOKEN = "8834292206:AAGIbtd57w50NPozFUQsGHKGxQ4b_BT99PY"

spell = SpellChecker(language="en")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
👋 Hello!

Welcome to the Translation Bot.

Features:

✅ English ↔ Arabic Translation
✅ IPA (Phonetic Transcription)
✅ Voice Pronunciation
✅ Spelling Correction
✅ Examples
✅ Synonyms

Developer:
@Xkadhem
"""
    await update.message.reply_text(text)


def contains_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)


def correct_spelling(sentence):
    words = re.findall(r"[A-Za-z']+", sentence)
    corrected = sentence
    changed = False

    for word in words:
        new = spell.correction(word)
        if new and new.lower() != word.lower():
            corrected = corrected.replace(word, new, 1)
            changed = True

    return corrected, changed


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    is_arabic = contains_arabic(text)

    if not is_arabic:
        corrected, changed = correct_spelling(text)

        if corrected != text:
            await update.message.reply_text(
                f"✍️ Did you mean?\n\n{corrected}"
            )

        text = corrected
        translated = GoogleTranslator(
            source="en",
            target="ar"
        ).translate(text)

        voice_text = text
        ipa_text = ipa.convert(text)

        if ipa_text.strip() == "" or "?" in ipa_text:
            ipa_text = "IPA not found"

        response = f"""🇬🇧 English
{text} > {translated}
ipa /{ipa_text}/
"""
    else:
        translated = GoogleTranslator(
            source="ar",
            target="en"
        ).translate(text)

        voice_text = translated
        ipa_text = ipa.convert(translated)

        if ipa_text.strip() == "" or "?" in ipa_text:
            ipa_text = "IPA not found"

        response = f"""🇮🇶 Arabic

{text}

🇬🇧 English

{translated}

🔤 IPA

{ipa_text}
"""

    example_text = ""
    synonym_text = ""

    if not is_arabic:
        try:
            r = requests.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{text.split()[0]}",
                timeout=10
            )

            if r.status_code == 200:
                data = r.json()[0]
                meanings = data.get("meanings", [])

                if meanings:
                    definitions = meanings[0].get("definitions", [])
                    if definitions:
                        ex = definitions[0].get("example")
                        if ex:
                            example_text = f"\n📖 Example:\n{ex}"

                    syn = meanings[0].get("synonyms", [])
                    if syn:
                        synonym_text = f"\n🔁 Synonyms:\n{', '.join(syn[:5])}"

        except Exception:
            pass

    response += example_text
    response += synonym_text

    filename = "voice.mp3"

    try:
        gTTS(
            text=voice_text,
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
    main()
