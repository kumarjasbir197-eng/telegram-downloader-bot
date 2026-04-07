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
    """Sync function with Flexible Formatting & iOS Impersonation"""
    ydl_opts = {
        # Flexible Logic: Try high-quality merge, then best single file
        'format': 'bestvideo+bestaudio/best' if is_video else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        'quiet': False, 
        'no_warnings': False,
        
        # 2026 Bypass: iOS client identity
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
                'skip': ['hls', 'dash']
            }
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
        'dynamic_mpd': True, # Required for PO Token plugin
    }
    
    # Apply Firefox cookies if available
    if os.path.exists(COOKIES_FILE):
        logger.info("Logic: Applying cookies.txt")
        ydl_opts['cookiefile'] = COOKIES_FILE
    
    if not is_video:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Logic: Starting download for {url}")
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if not is_video:
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename

# ===== TELEGRAM HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command from user {update.effective_user.id}")
    await update.message.reply_text("🚀 2026 Bypass Bot is Online! Send a YouTube or Instagram link.")

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
    
    await query.edit_message_text("⏳ Processing with 2026 logic... please wait.")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_func, url, query.data == "video")
        
        logger.info(f"Sending file: {file_path}")
        await query.message.reply_document(document=open(file_path, "rb"))
        os.remove(file_path) 
    except Exception as e:
        logger.error(f"Logic Error: {e}")
        await query.message.reply_text(f"⚠️ Error: {str(e)[:100]}")

# ===== MAIN RUNNER =====
if __name__ == "__main__":
    if not TOKEN or "provided" in TOKEN:
        logger.error("❌ CRITICAL: BOT_TOKEN is missing in Variables tab!")
    else:
        logger.info("✅ Token verified. Bot starting...")
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
