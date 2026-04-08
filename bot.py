import os
import time
import threading
import asyncio

from telethon import TelegramClient, events, Button
import yt_dlp
from flask import Flask
from waitress import serve

# ================= CONFIG =================
# Read environment variables with valid names
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

SESSION_NAME = "bot_session"
DOWNLOAD_FOLDER = "downloads"
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
DAILY_LIMIT = 5
HTTP_PORT = int(os.environ.get("PORT", 8080))  # JustRunMy.App uses $PORT

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

user_data = {}
user_limits = {}
download_queue = []

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ================= LIMITS =================
def check_limit(user_id):
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_limits:
        user_limits[user_id] = {"date": today, "count": 0}
    if user_limits[user_id]["date"] != today:
        user_limits[user_id] = {"date": today, "count": 0}
    if user_limits[user_id]["count"] >= DAILY_LIMIT:
        return False
    user_limits[user_id]["count"] += 1
    return True

# ================= PROGRESS =================
async def progress_hook(d, message):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "0%")
        speed = d.get("_speed_str", "N/A")
        eta = d.get("_eta_str", "N/A")
        text = (
            f"⬇️ Downloading...\n"
            f"📊 {percent}\n"
            f"⚡ {speed}\n"
            f"⏳ ETA: {eta}"
        )
        try:
            await message.edit(text)
        except:
            pass

def download_with_aria2(url, mode, message):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def hook(d):
        loop.run_until_complete(progress_hook(d, message))

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title).50s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "external_downloader": "aria2c",
        "external_downloader_args": [
            "-x", "16", "-s", "16", "-k", "1M", "--file-allocation=none"
        ],
    }

    if mode == "audio":
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                    }
                ],
            }
        )
    else:
        ydl_opts.update({"format": "bv*+ba/best"})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ================= QUEUE WORKER =================
def queue_worker():
    while True:
        if download_queue:
            chat_id, url, mode = download_queue.pop(0)
            try:
                msg = client.send_message(chat_id, "⏳ Starting download...")
                file_path = download_with_aria2(url, mode, msg)
                size = os.path.getsize(file_path)

                if size <= MAX_FILE_SIZE:
                    client.send_file(chat_id, file_path)
                else:
                    link = f"http://127.0.0.1:{HTTP_PORT}/{os.path.basename(file_path)}"
                    client.send_message(chat_id, f"⚠️ File too large\n📥 {link}")

                threading.Timer(
                    86400,
                    lambda: os.remove(file_path) if os.path.exists(file_path) else None,
                ).start()

            except Exception as e:
                client.send_message(chat_id, f"❌ Error: {e}")

        time.sleep(1)

threading.Thread(target=queue_worker, daemon=True).start()

# ================= FLASK KEEP‑ALIVE =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    serve(app, host="0.0.0.0", port=HTTP_PORT)

threading.Thread(target=run_flask, daemon=True).start()

# ================= BOT HANDLERS =================
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("🚀 Send any video/audio link!")

@client.on(events.NewMessage)
async def handler(event):
    if not event.text.startswith("http"):
        return
    chat_id = event.chat_id
    if not check_limit(chat_id):
        return await event.respond("❌ Daily limit reached")
    user_data[chat_id] = event.text
    await event.respond(
        "🎬 Choose format:",
        buttons=[
            [Button.inline("🎥 Video", b"video"), Button.inline("🎵 Audio", b"audio")]
        ],
    )

@client.on(events.CallbackQuery)
async def callback(event):
    chat_id = event.chat_id
    mode = event.data.decode()
    url = user_data.get(chat_id)
    if not url:
        return await event.edit("❌ Session expired")
    download_queue.append((chat_id, url, mode))
    await event.edit(f"🚀 {mode.capitalize()} downloading...")

# ================= RUN BOT =================
print("🔥 Bot running with ARIA2 + HTTP keep-alive...")
client.start()
client.run_until_disconnected()
