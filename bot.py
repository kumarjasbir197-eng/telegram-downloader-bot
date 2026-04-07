import os
import time
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ===== CONFIG =====
TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = 8503570215 
DOWNLOAD_PATH = "./downloads/"
COOKIES_FILE = "cookies.txt" 

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ===== DOWNLOAD LOGIC =====
def download_func(url, is_video):
    """Sync function with 2026 Anti-Block measures"""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if is_video else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # 2026 Bypass: Impersonate an iOS/Web client
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        # Custom User-Agent to match the player_client
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    }
    
    # Use cookies if present (Must be Firefox format)
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
    
    if not is_video:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not is_video:
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename

# ===== TELEGRAM HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot is Online! Send me a link.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return
    context.user_data["url"] = url
    
    keyboard = [[InlineKeyboardButton("🎬 Video", callback_data="video")],
                [InlineKeyboardButton("🎵 Audio", callback_data="audio")]]
    await update.message.reply_text("Format:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get("url")
    
    await query.edit_message_text("⏳ Processing with Bypass enabled...")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_func, url, query.data == "video")
        
        await query.message.reply_document(document=open(file_path, "rb"))
        os.remove(file_path) 
    except Exception as e:
        print(f"Error: {e}")
        await query.message.reply_text("⚠️ Failed. YouTube is blocking this IP. Ensure your cookies.txt is fresh from Firefox.")

# ===== RUN BOT =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Set BOT_TOKEN in Variables!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
