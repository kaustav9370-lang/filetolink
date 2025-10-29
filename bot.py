import os
import logging
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Your bot token from BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# The base URL of your deployed Vercel instance (e.g., https://your-vercel-app.vercel.app)
VERCEL_BASE_URL = os.environ.get("VERCEL_BASE_URL")

if not BOT_TOKEN or not VERCEL_BASE_URL:
    logger.error("BOT_TOKEN and VERCEL_BASE_URL environment variables must be set.")
    # Exit or raise an error if critical environment variables are missing
    # For a real application, you might want to handle this more gracefully
    # For this example, we'll proceed but the bot won't work without them
    pass

# --- Telegram Handlers ---

async def start(update: Update, context):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome! Send me a file and I will provide you with a streaming and download link "
        "from the Vercel file streamer. Make sure to set the VERCEL_BASE_URL environment variable."
    )

async def help_command(update: Update, context):
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text(
        "Just send me a file (video, audio, document) and I will generate the direct links for you."
    )

async def handle_file(update: Update, context):
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
        await message.reply_text("Please send a file (video, audio, or document).")
        return

    if not VERCEL_BASE_URL:
        await message.reply_text("Error: VERCEL_BASE_URL is not configured. Please set the environment variable.")
        return

    try:
        # Get the file link from Telegram
        # NOTE: This requires the bot to have the necessary permissions and the file size to be within limits.
        # The get_file() method will give us a File object which contains the file_path.
        # The full file URL is constructed as: https://api.telegram.org/file/bot<token>/<file_path>
        
        # We need to get the file object first to obtain the file_path
        file_obj = await context.bot.get_file(file_info.file_id)
        
        # The file_path is what we need to construct the direct Telegram file URL
        file_path = file_obj.file_path
        
        # Construct the full, direct Telegram file URL
        telegram_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # The Vercel streamer expects the file_url to be URL-encoded
        encoded_telegram_url = urllib.parse.quote_plus(telegram_file_url)

        # Construct the Vercel streaming and download links
        # The Vercel app uses the following endpoints (from vercel.json rewrite rules):
        # /watch/{filename}?file_url={encoded_telegram_url}
        # /download/{filename}?file_url={encoded_telegram_url}
        
        # Sanitize filename for URL
        safe_filename = urllib.parse.quote(file_name)
        
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
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, handle_file
    ))

    # Run the bot until the user presses Ctrl-C
    # For Render deployment, use application.run_polling() or application.run_webhook()
    # Since this is a simple bot, polling is often easier for initial setup.
    # For a proper Render deployment, you would typically use a webhook.
    # For simplicity and general use, we'll use polling here, assuming the user will adapt for Render's environment.
    logger.info("Starting bot in polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    if BOT_TOKEN and VERCEL_BASE_URL:
        main()
    else:
        print("Please set BOT_TOKEN and VERCEL_BASE_URL environment variables to run the bot.")
