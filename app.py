"""
SlackScope — AI Project Health Dashboard for Slack
Main entry point. Starts the Bolt app in Socket Mode.

Usage:
    python app.py

Prerequisites:
    1. Copy .env.example to .env and fill in tokens
    2. Create Slack App at https://api.slack.com/apps
    3. Enable Socket Mode, Event Subscriptions, Slash Commands
    4. Install app to workspace
"""

import logging
import sys

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import Config
from slack_handlers.events import register_events
from slack_handlers.commands import register_commands
from slack_handlers.actions import register_actions
from services.scheduler import ReportScheduler

# ── Logging Setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("slackscope")


def main():
    """Initialize and start SlackScope."""

    # ── Validate Config ───────────────────────────────────────
    print("🔭 SlackScope — AI Project Health Dashboard")
    print("=" * 45)

    if not Config.validate():
        print("\n⚠️  Fix the above issues and try again.")
        sys.exit(1)

    print("✅ Configuration validated")

    # ── Initialize Bolt App ───────────────────────────────────
    app = App(
        token=Config.SLACK_BOT_TOKEN,
        signing_secret=Config.SLACK_SIGNING_SECRET,
    )

    # ── Register Handlers ─────────────────────────────────────
    register_events(app)
    register_commands(app)
    register_actions(app)
    print("✅ Event, command, and action handlers registered")

    # ── Start Scheduler ───────────────────────────────────────
    scheduler = ReportScheduler(app.client)
    scheduler.start()

    if Config.MONITORED_CHANNELS:
        print(f"✅ Monitoring {len(Config.MONITORED_CHANNELS)} channels")
    else:
        print("ℹ️  No channels configured — use /slackscope configure")

    # ── Start Socket Mode ─────────────────────────────────────
    print("\n🚀 SlackScope is running! Press Ctrl+C to stop.")
    print("   • Mention @SlackScope in any channel to ask questions")
    print("   • Use /slackscope for commands")
    print("   • MCP server: run `python -m mcp_server.server` separately")
    print("")

    handler = SocketModeHandler(app, Config.SLACK_APP_TOKEN)

    try:
        handler.start()
    except KeyboardInterrupt:
        print("\n👋 SlackScope shutting down...")
        scheduler.stop()
        print("Done.")


if __name__ == "__main__":
    main()
