import logging
from telegram import Update
from telegram.ext import Application, ContextTypes
from config import BOT_TOKEN
from handlers.commands import handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# New: Error catching function
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Register all commands from the list
    for handler in handlers:
        app.add_handler(handler)

    # New: Register the error handler
    app.add_error_handler(error_handler)

    logging.info("🤖 Bot running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
