import os
import sys

# Make `import main` resolve to relay/main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub required env vars before main.py module-level code runs on import
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token:stub")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456789")
os.environ.setdefault("GH_PAT", "ghp_stub")
os.environ.setdefault("GH_REPO", "owner/repo")
