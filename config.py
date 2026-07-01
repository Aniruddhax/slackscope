"""
SlackScope Configuration
Loads environment variables and validates required tokens.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class Config:
    """Central configuration for SlackScope."""

    # ── Slack Tokens ──────────────────────────────────────────────
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")

    # ── Groq (FREE — OpenAI-compatible) ─────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"

    # ── SlackScope Settings ───────────────────────────────────────
    MONITORED_CHANNELS: list[str] = [
        ch.strip()
        for ch in os.getenv("MONITORED_CHANNELS", "").split(",")
        if ch.strip()
    ]
    REPORT_CHANNEL: str = os.getenv("REPORT_CHANNEL", "")
    DAILY_REPORT_TIME: str = os.getenv("DAILY_REPORT_TIME", "09:00")

    # ── Defaults ──────────────────────────────────────────────────
    # Max messages to fetch per channel scan
    MAX_MESSAGES_PER_SCAN: int = 50
    # Health score thresholds
    HEALTH_GOOD: int = 70
    HEALTH_WARNING: int = 40

    @classmethod
    def validate(cls) -> bool:
        """Check that all required tokens are set. Returns True if valid."""
        missing = []

        if not cls.SLACK_BOT_TOKEN or cls.SLACK_BOT_TOKEN.startswith("xoxb-your"):
            missing.append("SLACK_BOT_TOKEN")
        if not cls.SLACK_APP_TOKEN or cls.SLACK_APP_TOKEN.startswith("xapp-your"):
            missing.append("SLACK_APP_TOKEN")
        if not cls.SLACK_SIGNING_SECRET or cls.SLACK_SIGNING_SECRET == "your-signing-secret-here":
            missing.append("SLACK_SIGNING_SECRET")
        if not cls.GROQ_API_KEY or cls.GROQ_API_KEY.startswith("gsk_your"):
            missing.append("GROQ_API_KEY")

        if missing:
            print("❌ Missing required environment variables:")
            for var in missing:
                print(f"   • {var}")
            print("\n📝 Copy .env.example to .env and fill in your tokens:")
            print("   cp .env.example .env")
            return False

        return True
