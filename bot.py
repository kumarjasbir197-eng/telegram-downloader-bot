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
# Set this in your JustRunMy.App "Environment Variables" 
TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = 8503570215 
DOWNLOAD_PATH = "./downloads/"

# Ensure download directory exists
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ===== GLOBAL DATA =====
users = set()
download_count = 0
user_last_used = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Send me any video link!\n\nI support YouTube, Instagram, and more."
    )

# ===== HANDLE MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = update.message.text

    if not (url.startswith("http://") or url.startswith("https://")):
        return

    users.add(user_id)

    # Anti-spam (5 sec)
    if user_id in user_last_used and time.time() - user_last_used[user_id] < 5:
        await update.message.reply_text("⏳ Please wait a few seconds...")
        return

    user_last_used[user_id] = time.time()
    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("🎬 Video", callback_data="video")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio")]
    ]

    await update.message.reply_text(
        "Choose your format:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== DOWNLOAD LOGIC =====
def download_func(url, is_video):
    """Sync function to handle yt-dlp download"""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if is_video else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        # This helps bypass some basic bot detection
        'quiet': True,
        'no_warnings': True,
    }
    
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
            # If converted to audio, filename extension changes to .mp3
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

    await query.edit_message_text("⏳ Downloading... please wait.")

    is_video = (query.data == "video")

    try:
        # Run the blocking download in a separate thread to keep bot responsive
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_func, url, is_video)

        if os.path.exists(file_path):
            await query.message.reply_document(document=open(file_path, "rb"))
            download_count += 1
            os.remove(file_path)  # Cleanup to save server space
        else:
            await query.message.reply_text("❌ Error: File not found after download.")

    except Exception as e:
        print(f"Download Error: {e}")
        await query.message.reply_text("⚠️ Download failed. YouTube might be blocking this server's IP.")

# ===== ADMIN STATS =====
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📊 BOT STATS\n\n👥 Unique Users: {len(users)}\n⬇️ Total Downloads: {download_count}"
    )

# ===== MAIN =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: No BOT_TOKEN found in environment variables!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_handler))

        print("🤖 Bot is starting...")
        app.run_polling()
    
