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
# Set this in JustRunMy.App "Environment Variables"
TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = 8503570215 
DOWNLOAD_PATH = "./downloads/"
COOKIES_FILE = "cookies.txt" # Ensure this file is in your zip!

# Ensure download directory exists
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ===== GLOBAL DATA =====
users = set()
download_count = 0
user_last_used = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Send me any video link!\n\nI will try to download it using your session cookies."
    )

# ===== DOWNLOAD LOGIC =====
def download_func(url, is_video):
    """Sync function to handle yt-dlp download with Cookies"""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if is_video else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    # Use cookies if the file exists
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

# ===== BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global download_count
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("❌ Link expired. Please send it again.")
        return

    await query.edit_message_text("⏳ Downloading with cookies... please wait.")

    is_video = (query.data == "video")

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_func, url, is_video)

        if os.path.exists(file_path):
            await query.message.reply_document(document=open(file_path, "rb"))
            download_count += 1
            os.remove(file_path) 
        else:
            await query.message.reply_text("❌ Error: File not found.")

    except Exception as e:
        print(f"Download Error: {e}")
        await query.message.reply_text("⚠️ Download failed. YouTube is likely blocking the server IP even with cookies.")

# ===== MESSAGE HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = update.message.text
    if not url.startswith("http"): return

    users.add(user_id)
    if user_id in user_last_used and time.time() - user_last_used[user_id] < 5:
        await update.message.reply_text("⏳ Wait 5 seconds...")
        return

    user_last_used[user_id] = time.time()
    context.user_data["url"] = url

    keyboard = [[InlineKeyboardButton("🎬 Video", callback_data="video")],
                [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio")]]

    await update.message.reply_text("Choose format:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== MAIN =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: Set BOT_TOKEN in Environment Variables!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))
        print("🤖 Bot is starting...")
        app.run_polling()
        
