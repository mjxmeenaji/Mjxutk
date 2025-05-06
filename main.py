import logging
import os
import threading
import requests
import ffmpeg
from flask import Flask
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import asyncio

# Telegram token from environment
TOKEN = os.environ.get("BOT_TOKEN")

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

# To handle stopping the Flask app
def stop_flask():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()

async def download_file(url, filename):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = await asyncio.to_thread(requests.get, url, headers=headers, proxies=proxies, stream=True, timeout=60)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

async def convert_m3u8_to_mp4(m3u8_url, output_path):
    await asyncio.to_thread(ffmpeg.input(m3u8_url, protocol_whitelist="file,http,https,tcp,tls", user_agent="Mozilla/5.0")
                            .output(output_path, vcodec="copy", acodec="copy").run, overwrite_output=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Please send a .txt file containing Utkarsh links to start downloading."
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is stopping...")
    # Stop the Telegram bot and Flask server
    stop_flask()
    await update.message.reply_text("Shutting down gracefully...")
    await context.application.stop()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        ext = url.split('.')[-1].split('?')[0]
        file_name = f"/tmp/file_{i}.{ext if ext != 'm3u8' else 'mp4'}"
        try:
            if 'm3u8' in url:
                await update.message.reply_text(f"{i}/{len(links)}: M3U8 converting to MP4...")
                await convert_m3u8_to_mp4(url, file_name)
            else:
                await update.message.reply_text(f"{i}/{len(links)}: Downloading {ext.upper()}...")
                await download_file(url, file_name)

            await update.message.reply_document(document=open(file_name, 'rb'))
            os.remove(file_name)
        except Exception as e:
            await update.message.reply_text(f"Error downloading {url}: {e}")

    os.remove(file_path)
    await update.message.reply_text("All files downloaded and sent.")

if __name__ == '__main__':
    # Start dummy web server in a separate thread
    threading.Thread(target=run_web).start()

    # Start Telegram bot
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))  # Add /stop command handler
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("Bot is running...")
    app.run_polling()
    
