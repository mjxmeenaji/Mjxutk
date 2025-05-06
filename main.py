import logging
import os
import requests
import ffmpeg
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

proxies = {
    'http': 'socks5h://103.86.1.22:4145',
    'https': 'socks5h://103.86.1.22:4145'
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document: Document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("Sirf .txt file bhejiye jisme Utkarsh links ho.")
        return

    file_path = f"/tmp/{document.file_name}"
    await document.get_file().download_to_drive(file_path)

    with open(file_path, 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    await update.message.reply_text(f"Total {len(links)} links mile. Download start ho raha hai...")

    for i, url in enumerate(links, start=1):
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

    os.remove(file_path)
    await update.message.reply_text("All files downloaded and sent.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("Bot is running...")
    app.run_polling()
    
