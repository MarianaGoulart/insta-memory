from unittest.mock import AsyncMock, MagicMock, patch

from main import handle_message, TELEGRAM_CHAT_ID

WRONG_CHAT_ID = TELEGRAM_CHAT_ID + 1


async def test_wrong_chat_id_sends_no_reply():
    update = MagicMock()
    update.effective_chat.id = WRONG_CHAT_ID
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await handle_message(update, context)

    update.message.reply_text.assert_not_called()


async def test_non_instagram_url_sends_rejection():
    update = MagicMock()
    update.effective_chat.id = TELEGRAM_CHAT_ID
    update.message.text = "https://twitter.com/something"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await handle_message(update, context)

    update.message.reply_text.assert_called_once_with(
        "That doesn't look like an Instagram link."
    )


async def test_valid_url_triggers_dispatch_and_confirms():
    update = MagicMock()
    update.effective_chat.id = TELEGRAM_CHAT_ID
    update.message.text = "check this https://www.instagram.com/reel/ABC123/"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_resp)):
        await handle_message(update, context)

    update.message.reply_text.assert_called_once_with(
        "Got it, transcribing... I'll confirm when it's saved."
    )


async def test_github_api_failure_sends_error_reply():
    update = MagicMock()
    update.effective_chat.id = TELEGRAM_CHAT_ID
    update.message.text = "https://www.instagram.com/reel/ABC123/"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    with patch("asyncio.to_thread", new=AsyncMock(side_effect=Exception("timeout"))):
        await handle_message(update, context)

    update.message.reply_text.assert_called_once_with(
        "Something went wrong triggering the workflow. Try again."
    )
