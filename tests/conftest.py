"""Ensure dummy API keys exist before app modules import (so config.py loads
cleanly in CI without a real .env). load_dotenv won't override these."""
import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("MISTRAL_API_KEY", "test-key")
