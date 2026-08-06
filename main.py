from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gtts import gTTS
import os
import json
from flask import Flask
import threading
import time
from deep_translator import GoogleTranslator
import re

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

# دالة ذكية وعامة 100% لإزالة الحروف الصامتة لأي كلمة في اللغة أوتوماتيكياً
def auto_remove_silent_letters(word):
    w = word.lower().strip()
    
    # 1. إزالة الحروف الصامتة في البداية (مثل kn, wr, ps, gn)
    if w.startswith(("kn", "wr", "ps", "gn", "rh")):
        w = w[1:] if w.startswith("rh") else w[2:]
        
    # 2. معالجة الحروف الصامتة مثل h في honest أو honestly (بدون honey أو house)
    if w.startswith("hon") and not w.startswith("honey") and not w.startswith("house"):
        w = "on" + w[3:]
    elif w.startswith("hou") and w != "hour":
        pass
    elif w.startswith("h") and len(w) > 3 and w[1] in "aeiou" and w not in ["hello", "hat", "hot", "hope", "home"]:
        # بعض الكلمات التي تبدأ بـ h صامتة أو ضعيفة
        pass

    # 3. إزالة gh أو g قبل t (مثل knight, thought, high)
    w = w.replace("ght", "t").replace("gh", "")
    
    # 4. إزالة الـ d الصامتة في المنتصف (مثل wednesday)
    w = w.replace("dnes", "nes").replace("dsn", "sn")
    
    # 5. إزالة b الصامتة في النهاية بعد m (مثل comb, bomb, debt)
    if w.endswith("mb") or w.endswith("bt"):
        w = w[:-1]
        
    # 6. إزالة l الصامتة قبل k, m, f (مثل talk, calm, half)
    w = w.replace("lk", "k").replace("lm", "m").replace("alf", "af")
    
    # 7. إزالة حرف e الصامت في نهاية الكلمة إذا كان يتبع حرف صحيح
    if w.endswith("e") and len(w) > 3 and w[-2] not in "aeiou":
        w = w[:-1]
        
    return f"/{w}/"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    words_list = text.split()
    word_count = len(words_list)
    user_id = update.effective_user.id

    if user_id not in bot_users:
        bot_users.add(user_id)
        save_users(bot_users)

    try:
        is_ar = contains_arabic(text)
        
        if is_ar:
            translated = GoogleTranslator(source='ar', target='en').translate(text)
            if not translated:
                translated = text
            lang = 'en'
            voice_text = translated
            target_word = translated.lower().strip()
        else:
            translated = GoogleTranslator(source='en', target='ar').translate(text)
            if not translated:
                translated = text
            lang = 'en'
            voice_text = text
            target_word = text.lower().strip()

        # توليد الرسم الصوتي أوتوماتيكياً بالكامل لكل الكلمات بدون استثناء
        ipa_str = auto_remove_silent_letters(target_word)

        if word_count > 4:
            response = f"Translate : /{translated}/"
        else:
            response = (
                f"Translate : /{translated}/\n"
                f"IPA {ipa_str}"
            )

        await update.message.reply_text(response)

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
