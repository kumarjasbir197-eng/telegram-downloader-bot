import os
import time
import asyncio
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ===== VERBOSE LOGGING =====
# This will show you exactly what's happening in the dashboard logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = 8503570215 
DOWNLOAD_PATH = "./downloads/"
COOKIES_FILE = "cookies.txt" 

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ===== DOWNLOAD LOGIC =====
def download_func(url, is_video):
    """Sync function with 2026 Bypass measures"""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if is_video else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        'quiet': False, # Changed to False to see download errors in logs
        'no_warnings': False,
        'extractor_args': {'youtube': {'player_client': ['ios'], 'skip': ['hls', 'dash']}},
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    }
    
    if os.path.exists(COOKIES_FILE):
        logger.info("Using cookies.txt for download")
        ydl_opts['cookiefile'] = COOKIES_FILE
    else:
        logger.warning("No cookies.txt found! YouTube might block this")
    
    if not is_video:
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not is_video:
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text("🚀 Bot is Online! Send me a link.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return
    context.user_data["url"] = url
    keyboard = [[InlineKeyboardButton("🎬 Video", callback_data="video")],
                [InlineKeyboardButton("🎵 Audio", callback_data="audio")]]
    await update.message.reply_text("Select Format:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get("url")
    logger.info(f"Downloading: {url}")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_func, url, query.data == "video")
        await query.message.reply_document(document=open(file_path, "rb"))
        os.remove(file_path) 
    except Exception as e:
        logger.error(f"Download Error: {e}")
        await query.message.reply_text(f"⚠️ Error: {str(e)[:100]}")

# ===== MAIN =====
if __name__ == "__main__":
    if not TOKEN or "provided" in TOKEN:
        logger.error("❌ BOT_TOKEN is missing or is a placeholder! Check your Variables tab.")
    else:
        logger.info("✅ Token found. Starting Polling...")
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 2026 Bypass Mode Active. Send a YouTube/Instagram link!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return
    context.user_data["url"] = url
    
    keyboard = [[InlineKeyboardButton("🎬 Video", callback_data="video")],
                [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio")]]
    await update.message.reply_text("Select Format:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get("url")
    
    await query.edit_message_text("⏳ Bypassing YouTube blocks... please wait.")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_func, url, query.data == "video")
        
        await query.message.reply_document(document=open(file_path, "rb"))
        os.remove(file_path) 
    except Exception as e:
        print(f"Error: {e}")
        await query.message.reply_text("⚠️ Still blocked. YouTube has hard-flagged this IP. Please update your cookies.txt from Firefox.")

# ===== RUN BOT =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: Set BOT_TOKEN in the dashboard Variables!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
        
