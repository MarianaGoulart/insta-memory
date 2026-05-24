# Test guide — Instagram Capture Bot

This project has no automated test suite yet. This file defines what to test, how, and the acceptance bar for each component.

---

## 1. What to test automatically (unit tests)

These are pure logic — no network, no secrets needed. Use `pytest`.

### 1.1 URL regex (`relay/main.py` — `_INSTAGRAM_RE`)

Test file: `relay/tests/test_url_regex.py`

| Input | Expected |
|---|---|
| `https://www.instagram.com/reel/ABC123/` | match |
| `https://instagram.com/p/XYZ789` | match |
| `https://www.instagram.com/tv/DEF456/` | match |
| `https://www.instagram.com/stories/user/123/` | no match |
| `https://twitter.com/reel/ABC` | no match |
| `http://evil.com/instagram.com/reel/x` | no match |
| empty string | no match |

The regex must match on the domain + path, not just substring — test cases like the last two are the ones that catch naive `in` checks.

### 1.2 Chat ID whitelist

Test that `handle_message` returns early and sends no reply when `chat_id != TELEGRAM_CHAT_ID`. Mock `update.effective_chat.id` and `update.message.reply_text`. Assert `reply_text` is never called.

### 1.3 Invalid URL reply

Test that `handle_message` calls `reply_text("That doesn't look like an Instagram link.")` when the message contains no Instagram URL.

### 1.4 `shell=True` absence

Not a unit test — a grep check: `grep -r "shell=True" .` must return nothing. Run this in CI or as a pre-commit check.

---

## 2. What to test manually (smoke tests)

These require real credentials and can't be automated cheaply. Run them after any change to `relay/main.py` or `transcribe.yml`.

### 2.1 Happy path — public Reel

1. Send a public Instagram Reel URL to the bot in Telegram
2. Bot replies: "Got it, transcribing... I'll confirm when it's saved."
3. GitHub Actions run appears under Actions tab within ~5 seconds
4. Workflow completes successfully (~3–5 min)
5. Bot sends: "Transcribed and sent to your inbox."
6. Email arrives in inbox with subject `[Capture] YYYY-MM-DD HH:MM — <url>` and transcript body

### 2.2 Non-Instagram URL

Send any non-Instagram URL. Bot must reply: "That doesn't look like an Instagram link." No GitHub workflow is triggered.

### 2.3 Private or deleted Reel

Send a URL that is private or no longer exists. After retries (~15s), bot must reply with the yt-dlp error snippet. No email is sent.

### 2.4 No-speech video

Send a Reel that is music-only or silent. Bot must reply: "No speech detected in this video. Nothing saved." No email is sent.

### 2.5 Wrong chat ID

Test that a message from a different Telegram account (or forward from another chat) produces no bot reply and no workflow trigger. Check Railway logs to confirm the "Ignored message" warning fires.

---

## 3. How to add the unit tests

```
relay/
  main.py
  requirements.txt
  tests/
    __init__.py
    test_url_regex.py
    test_handle_message.py
```

Install test deps (not in `requirements.txt` — dev only):
```
pip install pytest pytest-asyncio
```

Run:
```
pytest relay/tests/
```

Use `unittest.mock.AsyncMock` for PTB `Update` and `ContextTypes` objects. Do not import or instantiate PTB's `Application` in unit tests — test the handler functions directly.

---

## 4. Acceptance bar before merging any PR

- All unit tests pass (`pytest relay/tests/`)
- `grep -r "shell=True" .` returns nothing
- Manual smoke test 2.1 (happy path) passes end-to-end
- No new secrets appear in logs (check Railway + Actions run logs)
