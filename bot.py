
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ===== CONFIG =====
# Grab the token from the Environment Variables panel in your host
TOKEN = os.environ.get("BOT_TOKEN") 
DOWNLOAD_PATH = "./downloads/"
ADMIN_ID = 8503570215  # Your Telegram ID

# Create the downloads folder if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ===== GLOBAL DATA =====
users = set()
download_count = 0
user_last_used = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Send me any video link!\n\nSupports YouTube, Instagram, Shorts, etc."
    )

# ===== HANDLE MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = update.message.text

    # Track users
    users.add(user_id)

    # Anti-spam (5 sec)
    if user_id in user_last_used and time.time() - user_last_used[user_id] < 5:
        await update.message.reply_text("⏳ Please wait a few seconds...")
        return

    user_last_used[user_id] = time.time()

    # Auto detect platform
    if "instagram.com" in url:
        platform = "📸 Instagram Reel detected"
    elif "youtube.com/shorts" in url or "youtu.be" in url:
        platform = "🎬 YouTube Short detected"
    else:
        platform = "🌐 General link detected"

    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("🎬 Video", callback_data="video")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio")]
    ]

    await update.message.reply_text(
        f"{platform}\nChoose format:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global download_count

    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")

    if not url:
        await query.edit_message_text("❌ No URL found")
        return

    await query.edit_message_text("⏳ Downloading...")

    # Download command
    if query.data == "video":
        cmd = f'yt-dlp -f "bv*+ba/best" --merge-output-format mp4 -o "{DOWNLOAD_PATH}%(title)s.%(ext)s" "{url}"'
    else:
        cmd = f'yt-dlp -x --audio-format mp3 -o "{DOWNLOAD_PATH}%(title)s.%(ext)s" "{url}"'

    # Execute the download
    os.system(cmd)

    # Increase download count
    download_count += 1

    # Get latest file
    try:
        files = sorted(
            os.listdir(DOWNLOAD_PATH),
            key=lambda x: os.path.getctime(os.path.join(DOWNLOAD_PATH, x))
        )
        
        if not files:
            await query.message.reply_text("❌ Download failed")
            return

        latest = files[-1]
        file_path = os.path.join(DOWNLOAD_PATH, latest)

        # Send the file
        await query.message.reply_document(document=open(file_path, "rb"))
        
        # Optional: Delete the file after sending to save server space
        os.remove(file_path) 
        
    except Exception as e:
        await query.message.reply_text("⚠️ File too large to send or an error occurred.")
        print(f"Error: {e}")

# ===== ADMIN STATS =====
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        f"📊 BOT STATS\n\n👥 Users: {len(users)}\n⬇️ Downloads: {download_count}"
    )

# ===== MAIN =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable is missing!")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")
    app.run_polling()
