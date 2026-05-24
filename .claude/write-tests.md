# Security Audit — Instagram Capture Bot

Claude Code should verify every item in this checklist before the build is considered done. Each item has a pass condition — if it can't be met, flag it rather than skip it.

---

## 1. Secrets handling

**1.1 No hardcoded secrets**
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GH_PAT`, `GH_REPO` must never appear in source code
- Check: `grep -r "bot[0-9]\|AAF\|ghp_" .` should return nothing in `.py` files

**1.2 No secrets in logs**
- The relay must not `print()` or `log()` the bot token, PAT, or chat ID at any point — not even partially
- Check: review all logging statements in `relay/main.py`

**1.3 `.gitignore` covers local env files**
- `.env`, `.env.*`, `*.pem`, `*.key` must be in `.gitignore`
- The repo must not contain any of these files

**1.4 GitHub Actions secrets are referenced correctly**
- Workflow uses `${{ secrets.NAME }}` syntax — never `${{ env.NAME }}` for sensitive values
- Secrets are not echoed in `run:` steps (e.g. no `echo $TOKEN`)

---

## 2. Input validation

**2.1 Telegram chat ID whitelist is enforced first**
- The relay must check `chat_id == TELEGRAM_CHAT_ID` before doing anything else with the message
- Any message from an unknown chat ID is silently dropped — no reply, no log of the content

**2.2 Instagram URL validation before passing to yt-dlp**
- URL must be validated against an allowlist pattern before being passed anywhere
- Acceptable patterns: `instagram.com/reel/`, `instagram.com/p/`, `instagram.com/tv/`
- Validation must use a regex match on the domain + path — not just a string contains check
- If validation fails: reply "That doesn't look like an Instagram link." and stop

**2.3 URL is never interpolated into a shell string**
- `yt-dlp` and Whisper must be called via `subprocess.run([...], shell=False)` with the URL as a list element
- `shell=True` is forbidden anywhere in the codebase — it opens command injection
- Check: `grep -r "shell=True" .` must return nothing

---

## 3. GitHub Actions permissions

**3.1 Workflow declares minimal permissions**
The workflow file must include an explicit permissions block at the top:
```yaml
permissions:
  contents: write
```
Nothing else. Do not use the default broad permissions.

**3.2 PAT scope is the minimum needed**
- The `GH_PAT` used by Railway only needs to trigger `repository_dispatch` and push commits to one repo
- Recommended: use a fine-grained PAT (GitHub → Settings → Developer settings → Fine-grained tokens) scoped to the `instagram-capture-bot` repo only, with:
  - **Contents:** Read and write
  - **Actions:** Read and write (for workflow dispatch)
- The classic `repo` scope works but gives broader access than needed — flag this to the user if a fine-grained token wasn't used

**3.3 No sensitive data written to workflow logs**
- The `TELEGRAM_BOT_TOKEN` and `GH_PAT` must not appear in any `echo`, `run`, or debug step
- Whisper output and transcript content are fine to log

---

## 4. Dependency management

**4.1 `yt-dlp` is unpinned by design**
- Intentional — Instagram workarounds require staying on latest
- Document this clearly in `relay/requirements.txt` with a comment

**4.2 All other dependencies are pinned**
- `python-telegram-bot`, `requests`, and any other packages must have pinned versions in `requirements.txt`
- Do not use `>=` or unpinned entries for anything except `yt-dlp`

**4.3 Whisper installed from the correct source**
- Use `openai-whisper` (the open-source package), not the `openai` SDK
- Verify the package name in the workflow install step

---

## 5. File handling

**5.1 Temp audio files are deleted after transcription**
- `yt-dlp` downloads audio to a temp file — this must be explicitly deleted after Whisper finishes, whether transcription succeeds or fails
- Use a `try/finally` block to guarantee cleanup

**5.2 No path traversal in filenames**
- The output `.md` filename is derived from the current UTC timestamp — not from any user input
- Verify: no part of the Instagram URL is used in the filename

**5.3 `captures/` commits are clean**
- Only `.md` files should ever be committed to `captures/`
- Audio files, temp files, and logs must not end up in the repo

---

## 6. Error handling

**6.1 No raw exceptions exposed to the user**
- Telegram replies must never contain Python tracebacks or internal paths
- Catch all exceptions at the top level and send a generic message: "Something went wrong. Try again, or check if the link is public."
- Log the full traceback to stdout (visible in Railway/Actions logs) for debugging

**6.2 yt-dlp failure is handled, not crashed**
- Private content, deleted videos, and rate limits all cause `yt-dlp` to exit non-zero
- The workflow must catch this, retry 3 times with a 5-second delay, then send a Telegram message if all attempts fail — it must not leave the workflow in a failed state with no user notification

**6.3 Empty repo edge case**
- If `captures/` is empty or doesn't exist yet, the Cowork sync task must handle it gracefully — not crash

---

## 7. Railway-specific

**7.1 Environment variables are set in Railway dashboard — not in code**
- The `relay/` folder must not contain a `.env` file
- Railway injects env vars at runtime — document this in the deploy instructions

**7.2 The relay does not expose any HTTP endpoints**
- Polling mode only — no `web` server, no open port
- Verify there is no `Flask`, `FastAPI`, or `http.server` import in `relay/main.py`
