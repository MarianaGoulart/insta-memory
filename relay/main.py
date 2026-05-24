import asyncio
import os
import re
import logging
import requests
from telegram import Update
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
GH_PAT = os.environ["GH_PAT"]
GH_REPO = os.environ["GH_REPO"]

_INSTAGRAM_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[\w-]+/?"
)

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext._updater").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id != TELEGRAM_CHAT_ID:
        logger.warning("Ignored message from chat_id %d (expected %d)", chat_id, TELEGRAM_CHAT_ID)
        return

    text = update.message.text or ""
    match = _INSTAGRAM_RE.search(text)
    if not match:
        await update.message.reply_text("That doesn't look like an Instagram link.")
        return

    url = match.group(0)
    try:
        resp = await asyncio.to_thread(
            requests.post,
            f"https://api.github.com/repos/{GH_REPO}/dispatches",
            json={"event_type": "transcribe", "client_payload": {"url": url}},
            headers={
                "Authorization": f"token {GH_PAT}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        await update.message.reply_text("Got it, transcribing... I'll confirm when it's saved.")
    except Exception:
        logger.exception("Failed to trigger GitHub workflow")
        await update.message.reply_text("Something went wrong triggering the workflow. Try again.")


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Conflict):
        logger.debug("Startup conflict — old instance still shutting down, PTB will retry")
        return
    logger.exception("Unhandled error", exc_info=context.error)


def main() -> None:
    logger.info("Bot starting. Whitelisted chat_id: %d", TELEGRAM_CHAT_ID)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(handle_error)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
