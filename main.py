import logging
import os
import threading
import requests
import ffmpeg
from flask import Flask
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from pyrogram import Client

# Telegram token from environment
TOKEN = os.environ.get("BOT_TOKEN")

# Replace with your api_id and api_hash from my.telegram.org
API_ID = '23069582'  
API_HASH = 'b3b56eaf67828684f54d540f684fdf1f'

proxies = {
    'http': 'socks5h://103.86.1.22:4145',
    'https': 'socks5h://103.86.1.22:4145'
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dummy HTTP server to keep Koyeb instance alive
app_flask = Flask(__name__)

@app_flask.route("/")
def health():
    return "Bot is alive!"

def run_web():
    app_flask.run(host="0.0.0.0", port=8000)

def download_file(url, filename):
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, proxies=proxies, stream=True, timeout=60)
    r.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

def convert_m3u8_to_mp4(m3u8_url, output_path):
    (
        ffmpeg
        .input(m3u8_url, protocol_whitelist="file,http,https,tcp,tls", user_agent="Mozilla/5.0")
        .output(output_path, vcodec="copy", acodec="copy")
        .run(overwrite_output=True)
    )

# Variable to track whether the bot is processing
is_processing = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Please send a .txt file containing Utkarsh links to start downloading."
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_processing
    if is_processing:
        is_processing = False
        await update.message.reply_text("Downloading process stopped.")
    else:
        await update.message.reply_text("No active process to stop.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_processing
    if is_processing:
        await update.message.reply_text("A process is already running. Please stop it first.")
        return

    is_processing = True
    document: Document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("Sirf .txt file bhejiye jisme Utkarsh links ho.")
        return

    file_path = f"/tmp/{document.file_name}"

    # Await the coroutine correctly
    file = await document.get_file()  # Await the coroutine
    await file.download_to_drive(file_path)  # Download to drive

    with open(file_path, 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    await update.message.reply_text(f"Total {len(links)} links mile. Download start ho raha hai...")

    for i, url in enumerate(links, start=1):
        if not is_processing:
            await update.message.reply_text("Process was stopped.")
            break

        ext = url.split('.')[-1].split('?')[0]
        file_name = f"/tmp/file_{i}.{ext if ext != 'm3u8' else 'mp4'}"
        try:
            if 'm3u8' in url:
                await update.message.reply_text(f"{i}/{len(links)}: M3U8 converting to MP4...")
                convert_m3u8_to_mp4(url, file_name)
            else:
                await update.message.reply_text(f"{i}/{len(links)}: Downloading {ext.upper()}...")
                download_file(url, file_name)

            await update.message.reply_document(document=open(file_name, 'rb'))
            os.remove(file_name)
        except Exception as e:
            await update.message.reply_text(f"Error downloading {url}: {e}")

    is_processing = False
    os.remove(file_path)
    await update.message.reply_text("All files downloaded and sent.")

if __name__ == '__main__':
    # Start dummy web server in a separate thread
    threading.Thread(target=run_web).start()

    # Start Pyrogram client with API_ID and API_HASH
    app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot is running...")
    app.run()
    
