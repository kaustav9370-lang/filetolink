import os
import logging
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# The base URL of your deployed Vercel instance (e.g., https://your-vercel-app.vercel.app)
VERCEL_BASE_URL = os.environ.get("VERCEL_BASE_URL")

if not BOT_TOKEN or not VERCEL_BASE_URL:
    logger.error("BOT_TOKEN and VERCEL_BASE_URL environment variables must be set.")
    # The bot will still run, but the handlers will check for these variables before processing a file.

# --- Telegram Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome! Send me a file and I will provide you with a streaming and download link "
        "from the Vercel file streamer. Make sure to set the VERCEL_BASE_URL environment variable."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text(
        "Just send me a file (video, audio, document) and I will generate the direct links for you."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming files and generates Vercel streaming/download links."""
    message = update.message
    file_info = None
    file_name = None

    # Check for different file types
    if message.video:
        file_info = message.video
        file_name = file_info.file_name or f"video_{file_info.file_unique_id}.mp4"
    elif message.audio:
        file_info = message.audio
        file_name = file_info.file_name or f"audio_{file_info.file_unique_id}.mp3"
    elif message.document:
        file_info = message.document
        file_name = file_info.file_name or f"document_{file_info.file_unique_id}"
    
    if not file_info:
        # This case should ideally be caught by the filter, but as a fallback:
        await message.reply_text("Please send a file (video, audio, or document).")
        return

    if not VERCEL_BASE_URL:
        await message.reply_text("Error: VERCEL_BASE_URL is not configured. Please set the environment variable.")
        return
    
    if not BOT_TOKEN:
        await message.reply_text("Error: BOT_TOKEN is not configured. Please set the environment variable.")
        return

    try:
        # 1. Get the File object from Telegram to obtain the file_path
        # This step requires the BOT_TOKEN and is the critical part that allows the Vercel app to fetch the file.
        file_obj = await context.bot.get_file(file_info.file_id)
        
        # The file_path is used to construct the direct Telegram file URL
        file_path = file_obj.file_path
        
        # 2. Construct the full, direct Telegram file URL
        # Format: https://api.telegram.org/file/bot<token>/<file_path>
        telegram_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # 3. URL-encode the Telegram file URL for the Vercel app's query parameter
        # We use quote_plus to encode spaces as '+' which is standard for query parameters
        encoded_telegram_url = urllib.parse.quote_plus(telegram_file_url)

        # 4. Construct the final Vercel streaming and download links
        
        # Sanitize filename for URL path (standard quote)
        safe_filename = urllib.parse.quote(file_name)
        
        # Vercel endpoints (based on vercel.json rewrite rules):
        # /watch/{filename}?file_url={encoded_telegram_url}
        # /download/{filename}?file_url={encoded_telegram_url}
        
        streaming_link = f"{VERCEL_BASE_URL}/watch/{safe_filename}?file_url={encoded_telegram_url}"
        download_link = f"{VERCEL_BASE_URL}/download/{safe_filename}?file_url={encoded_telegram_url}"
        
        response_text = (
            f"**File:** `{file_name}`\n\n"
            f"**Streaming Link:**\n`{streaming_link}`\n\n"
            f"**Download Link:**\n`{download_link}`\n\n"
            "The Vercel application will stream the file directly from Telegram's servers."
        )
        
        await message.reply_text(response_text, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await message.reply_text(f"An error occurred while generating the links: {e}")


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("Cannot start bot: BOT_TOKEN is not configured.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Message handler for files (video, audio, document) but excluding commands
    file_filter = filters.ATTACHMENT | filters.VIDEO | filters.AUDIO | filters.DOCUMENT
    application.add_handler(MessageHandler(file_filter & ~filters.COMMAND, handle_file))

    # Run the bot
    # For Render, you typically use a web service that runs a command like:
    # python bot.py
    # This will start the polling loop.
    logger.info("Starting bot in polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
