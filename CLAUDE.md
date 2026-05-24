# CLAUDE.md — Instagram Capture Bot

## What this is

A Telegram bot that receives an Instagram Reel link, downloads the audio with `yt-dlp`, transcribes it with OpenAI Whisper, and commits a raw `.md` file to this repo. A separate Cowork scheduled task handles enrichment (title + key points) and moves finished files to the user's local folder.

Solo use. One user. No auth complexity beyond a chat ID whitelist.

---

## Repo structure

```
├── .github/
│   └── workflows/
│       └── transcribe.yml        # triggered by repository_dispatch
├── relay/
│   ├── main.py                   # Telegram listener — runs on Railway
│   └── requirements.txt
├── captures/                     # raw .md files committed by Actions
├── _state/
│   └── .last_sync                # UTC timestamp of last Cowork sync
└── CLAUDE.md
```

---

## Architecture

```
[Telegram] → [Railway relay] → [repository_dispatch] → [GitHub Actions]
                                                              ↓
                                                    yt-dlp downloads audio
                                                              ↓
                                                    Whisper transcribes
                                                              ↓
                                                    raw .md committed to captures/
                                                              ↓
                                                    Telegram confirmation sent
```

Cowork sync (runs separately, twice a week on user's laptop):
```
captures/ (raw .md files) → Claude enrichment → 09_Captures/ (finished files)
```

---

## Component 1: Railway relay (`relay/main.py`)

A minimal Python script using `python-telegram-bot` in polling mode.

**What it does:**
1. Listens for messages from the whitelisted chat ID only — ignore everything else silently
2. Checks if the message contains an Instagram URL (reel, p, or tv path) — if not, reply: "That doesn't look like an Instagram link."
3. If valid: fires a `repository_dispatch` event to GitHub with the URL as payload
4. Replies immediately: "Got it, transcribing... I'll confirm when it's saved."
5. On any error calling GitHub API: reply "Something went wrong triggering the workflow. Try again."

**Environment variables (set in Railway):**
- `TELEGRAM_BOT_TOKEN` — bot token from BotFather
- `TELEGRAM_CHAT_ID` — Mariana's Telegram chat ID (whitelist)
- `GH_PAT` — GitHub Personal Access Token with `repo` scope
- `GH_REPO` — repo in `owner/repo` format (e.g. `mariana/instagram-capture-bot`)

**Requirements:**
```
python-telegram-bot==20.7
requests==2.31.0
```

---

## Component 2: GitHub Actions workflow (`.github/workflows/transcribe.yml`)

Triggered by `repository_dispatch` with event type `transcribe`.

Payload received: `{ "url": "https://www.instagram.com/reel/..." }`

**Steps:**
1. Check out repo
2. Install Python dependencies: `yt-dlp` (latest, not pinned), `openai-whisper`, `requests`
3. Download audio with `yt-dlp` — audio only, best quality, output to temp file
4. Transcribe with Whisper `base` model
5. Validate transcript (see quality checks below)
6. Write raw `.md` file to `captures/`
7. Commit and push
8. Send Telegram confirmation (or error message)

**Quality checks before committing:**
- Transcript length < 100 characters → skip commit, send Telegram message: "No speech detected in this video. Nothing saved."
- `yt-dlp` fails (private, unavailable, rate-limited) → retry 3 times with 5s delay → if all fail, send Telegram: "Couldn't download this one. Check if it's private or try again later."
- Whisper `no_speech_prob` average across segments > 0.8 → treat as no speech, same message as above

**Raw `.md` file format:**
```markdown
---
captured: 2026-05-24T14:30:22Z
source: https://www.instagram.com/reel/ABC123/
---

[raw transcript text]
```

**File naming:** `YYYY-MM-DDThhmmsZ_raw.md` (UTC, derived from capture time)
Example: `2026-05-24T143022Z_raw.md`

**Secrets required (set in GitHub repo settings):**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GH_PAT` — needed to push commits (GITHUB_TOKEN has limited permissions for dispatch-triggered workflows)

---

## Component 3: `_state/.last_sync`

A single-line file containing the UTC timestamp of the last successful Cowork sync.

```
2026-05-24T14:30:22Z
```

**Rules:**
- Created on first sync with timestamp `1970-01-01T00:00:00Z` (processes everything)
- Updated only after a fully successful sync run — never mid-run
- Committed back to the repo by the Cowork sync script after each successful run

The Cowork sync task (built separately in Cowork) uses this to determine which files in `captures/` are new. It parses the timestamp from each filename and skips anything older than or equal to the `.last_sync` value.

---

## What NOT to build

- No categorisation or sub-folder logic
- No support for non-Instagram URLs in this version
- No web UI, no database
- No user management — single chat ID whitelist only
- No editing or deleting captures via the bot
- No Claude API calls — enrichment happens in Cowork, not here

---

## Build order

1. `relay/main.py` + `relay/requirements.txt`
2. `.github/workflows/transcribe.yml`
3. `_state/.last_sync` (initial file with epoch timestamp)
4. Smoke test: send a real Instagram Reel link through Telegram, verify `.md` file appears in `captures/`

---

## Before making any changes

1. Read [`audit.md`](audit.md) and [`write-tests.md`](write-tests.md) before touching any code.
2. For any feature change, create a new branch first — never commit feature work directly to `main` or `master`.

---

## Known constraints

- `yt-dlp` + Instagram: works on public Reels only. Private content and Stories will fail — handle gracefully, never crash.
- Whisper `base` may struggle with heavy accents or low audio quality — acceptable tradeoff for speed. Can swap to `small` model later by changing one line.
- Railway free tier is sufficient for a relay this lightweight. If Railway changes policies, the relay is ~50 lines of Python and can be moved anywhere in under an hour.
