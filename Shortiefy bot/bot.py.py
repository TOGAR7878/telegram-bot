import sqlite3
import re
import requests
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Config
BOT_TOKEN = "8173485072:AAG5TbdvJG-OC4OBbKp1s7s3TzNs1mYM104"
SHORTENER_URL = "https://shortiefy.com/api"

# SQLite DB Setup
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        api_key TEXT
    )
""")
conn.commit()

# Helper Functions
def get_api_key(user_id):
    c.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else None

def set_api_key(user_id, api_key):
    c.execute("REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, api_key))
    conn.commit()

def shorten_url(api_key, long_url):
    params = {'api': api_key, 'url': long_url}
    try:
        res = requests.get(SHORTENER_URL, params=params)
        if res.status_code == 200:
            data = json.loads(res.text)
            return data.get("shortenedUrl", "Shortening failed").replace("\\/", "/")
        else:
            return "Shortening failed."
    except Exception as e:
        return f"Error: {e}"

def is_channel_link(url):
    return "https://t.me/" in url or "t.me/" in url

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {name}!\n\n"
        "I am your Shortiefy Link Converter Bot.\n"
        "I can convert your links using your own Shortiefy.com API.\n\n"
        "1. Go To 👉 https://shortiefy.com/member/tools/api\n"
        "2. Then Copy API Key\n"
        "3. Than Type /api than give a single space and than paste your API Key (see example to understand more...)\n\n"
        "(See Example.👇) Example: /api 04e8ee10b5f123456a640c8f33195abc\n\n"
        "Now send links or media with links to get shortened links back!"
    )

async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) == 1 and re.match(r"^[a-f0-9]{40}$", context.args[0]):
        set_api_key(user_id, context.args[0])
        await update.message.reply_text("API key saved successfully!")
    else:
        await update.message.reply_text("Invalid API key format. Please send a valid 40-character key.")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "cantact us:\n"
        "shortefy@gmail.com (📢cantact us for any help and inquiry)\n"
    )

# Main Handler
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    api_key = get_api_key(user_id)

    if not api_key:
        await update.message.reply_text("Please set your API key first using /api command.")
        return

    # Handle Photo + Caption
    if update.message.photo and update.message.caption:
        caption = update.message.caption
        urls = re.findall(r'https?://\S+', caption)

        for url in urls:
            if is_channel_link(url):
                continue
            short = shorten_url(api_key, url)
            caption = caption.replace(url, short)

        await update.message.reply_photo(photo=update.message.photo[-1].file_id, caption=caption)
        return

    # Handle Text Messages
    if update.message.text:
        text = update.message.text

        if text.startswith("/help"):
            return  # Already handled by command

        urls = re.findall(r'https?://\S+', text)

        if not urls:
            await update.message.reply_text("No link found to shorten.")
            return

        for url in urls:
            if is_channel_link(url):
                continue
            short = shorten_url(api_key, url)
            text = text.replace(url, short)

        await update.message.reply_text(text)

# Start Bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("api", set_api))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(MessageHandler(filters.ALL, handle_all))

    app.run_polling()