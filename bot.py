
import os
import subprocess
import uuid
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Set your headers here
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.classx.co.in"
}

# Function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me an Appx HLS (.m3u8) link to download the video.")

# Function to handle the video download link
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if ".m3u8" in url:
        await update.message.reply_text("Downloading video... please wait.")

        # Create a unique filename for each download
        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        
        # Prepare headers string for yt-dlp
        headers_str = ",".join([f"{k}:{v}" for k, v in HEADERS.items()])

        # yt-dlp command to download the video
        cmd = [
            "yt-dlp",
            url,
            "-o", filename,
            "--downloader", "ffmpeg",
            "--hls-prefer-ffmpeg",
            "--add-header", headers_str
        ]
        
        # Run the command to download the video
        subprocess.run(cmd)

        # Check if the video file is downloaded successfully
        if os.path.exists(filename):
            await update.message.reply_video(video=open(filename, 'rb'))
            os.remove(filename)  # Remove the file after sending it to the user
        else:
            await update.message.reply_text("Download failed or headers rejected.")
    else:
        await update.message.reply_text("Please send a valid Appx HLS .m3u8 link.")

# Main function to set up the bot
def main():
    # Replace with your actual bot token
    bot_token = "7928417328:AAHoB1UJmmPXZ4lRZ7CfEcuw7-5EGuQlf3M"

    # Build the bot application
    app = ApplicationBuilder().token(bot_token).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))  # Start command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))  # Text message handler

    # Start the bot and begin polling for new messages
    app.run_polling()

if __name__ == "__main__":
    main()
  
