"""
Slash Command Handlers
Handles /slackscope commands for direct interaction.
"""

import re
import logging
from slack_bolt import App
from services.rts_search import RTSSearch
from agents.health_analyzer import HealthAnalyzer
from agents.report_generator import ReportGenerator
from agents.team_analyzer import TeamAnalyzer
from services.trend_tracker import TrendTracker
from ui.blocks import BlockKitUI
from config import Config

logger = logging.getLogger(__name__)


def register_commands(app: App):
    """Register slash command handlers."""

    rts = RTSSearch(app.client)
    analyzer = HealthAnalyzer()
    team_analyzer = TeamAnalyzer()
    trend_tracker = TrendTracker()

    @app.command("/slackscope")
    def handle_slackscope_command(ack, command, respond, client):
        """
        Handle /slackscope commands.

        Usage:
            /slackscope help                — Show usage info
            /slackscope health #channel     — Health report for a channel
            /slackscope report              — Trigger daily report
            /slackscope configure           — Open config modal
        """
        ack()  # Acknowledge within 3 seconds

        text = command.get("text", "").strip()
        user_id = command.get("user_id", "")

        if not text or text == "help":
            respond(blocks=BlockKitUI.help_message(), text="SlackScope help")
            return

        # Parse subcommand
        parts = text.split(maxsplit=1)
        subcommand = parts[0].lower()

        if subcommand == "health":
            _handle_health(parts, respond, rts, analyzer, client)

        elif subcommand == "report":
            _handle_report(respond, rts, analyzer, client)

        elif subcommand == "configure":
            _handle_configure(command, client)

        elif subcommand == "team":
            _handle_team(parts, respond, rts, team_analyzer, client)

        elif subcommand == "trends":
            _handle_trends(parts, respond, trend_tracker)

        else:
            respond(
                blocks=BlockKitUI.error_message(
                    f"Unknown command: `{subcommand}`.\nUse `/slackscope help` for available commands."
                ),
                text="Unknown command",
            )


def _handle_health(parts: list, respond, rts: RTSSearch, analyzer: HealthAnalyzer, client=None):
    """Handle /slackscope health #channel."""
    if len(parts) < 2:
        respond(
            blocks=BlockKitUI.error_message("Please specify a channel: `/slackscope health #channel-name`"),
            text="Missing channel",
        )
        return

    # Extract channel ID from Slack's <#C123|name> format
    channel_ref = parts[1]
    channel_match = re.search(r"<#([A-Z0-9]+)\|?([^>]*)>", channel_ref)

    if channel_match:
        channel_id = channel_match.group(1)
        channel_name = channel_match.group(2) or "channel"
    else:
        # Try as plain channel name — look up channel ID via API
        channel_name = channel_ref.strip("#").strip()
        channel_id = _lookup_channel_id(channel_name, client)
        if not channel_id:
            respond(
                blocks=BlockKitUI.error_message(
                    f"Could not find channel `#{channel_name}`. Make sure the channel exists and the bot is a member."
                ),
                text="Channel not found",
            )
            return

    respond(text=f"🔭 Analyzing #{channel_name}...")

    # Fetch messages via RTS + conversation history
    messages = rts.search_recent_activity(channel_id)
    rts_results = rts.search_channel_context("project updates progress blockers", channel_id)

    # Merge and deduplicate
    all_messages = _merge_unique(messages, rts_results)

    # Analyze
    health_data = analyzer.analyze_channel_health(channel_name, all_messages)

    # Respond with rich Block Kit card
    blocks = BlockKitUI.health_report_card(channel_name, health_data)
    respond(blocks=blocks, text=f"Health report for #{channel_name}")


def _lookup_channel_id(channel_name: str, client) -> str | None:
    """Look up a channel ID by name using conversations.list."""
    if not client:
        return None
    try:
        cursor = None
        while True:
            kwargs = {"types": "public_channel", "limit": 200}
            if cursor:
                kwargs["cursor"] = cursor
            result = client.conversations_list(**kwargs)
            for ch in result.get("channels", []):
                if ch["name"] == channel_name:
                    return ch["id"]
            cursor = result.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    except Exception as e:
        logger.error(f"Channel lookup failed: {e}")
    return None


def _handle_report(respond, rts: RTSSearch, analyzer: HealthAnalyzer, client):
    """Handle /slackscope report — trigger manual daily report."""
    monitored = Config.MONITORED_CHANNELS

    if not monitored:
        respond(
            blocks=BlockKitUI.error_message(
                "No channels configured for monitoring.\n"
                "Set `MONITORED_CHANNELS` in your .env file or use `/slackscope configure`."
            ),
            text="No channels configured",
        )
        return

    respond(text=f"🔭 Generating report for {len(monitored)} channels...")

    reports = []
    for channel_id in monitored:
        info = rts.get_channel_info(channel_id)
        channel_name = info["name"] if info else channel_id

        messages = rts.search_recent_activity(channel_id)
        health_data = analyzer.analyze_channel_health(channel_name, messages)

        reports.append({
            "channel_name": channel_name,
            "health_data": health_data,
        })

    # Post dashboard
    blocks = BlockKitUI.daily_dashboard(reports)
    respond(blocks=blocks, text="SlackScope Daily Dashboard")


def _handle_configure(command: dict, client):
    """Open configuration modal."""
    trigger_id = command.get("trigger_id")

    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "slackscope_config",
            "title": {"type": "plain_text", "text": "🔭 SlackScope Config"},
            "submit": {"type": "plain_text", "text": "Save"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Select channels for SlackScope to monitor:",
                    },
                },
                {
                    "type": "input",
                    "block_id": "channels_block",
                    "element": {
                        "type": "multi_conversations_select",
                        "action_id": "selected_channels",
                        "placeholder": {"type": "plain_text", "text": "Pick channels..."},
                        "filter": {"include": ["public", "private"]},
                    },
                    "label": {"type": "plain_text", "text": "Monitored Channels"},
                },
                {
                    "type": "input",
                    "block_id": "report_channel_block",
                    "element": {
                        "type": "conversations_select",
                        "action_id": "report_channel",
                        "placeholder": {"type": "plain_text", "text": "Pick a channel..."},
                        "filter": {"include": ["public"]},
                    },
                    "label": {"type": "plain_text", "text": "Report Channel"},
                },
            ],
        },
    )


def _merge_unique(list1: list[dict], list2: list[dict]) -> list[dict]:
    """Merge and deduplicate message lists."""
    seen = set()
    merged = []
    for msg in list1 + list2:
        ts = msg.get("ts", "")
        if ts not in seen:
            seen.add(ts)
            merged.append(msg)
    return merged


def _handle_team(parts: list, respond, rts: RTSSearch, team_analyzer, client=None):
    """Handle /slackscope team #channel — team productivity analysis."""
    if len(parts) < 2:
        respond(
            blocks=BlockKitUI.error_message("Please specify a channel: `/slackscope team #channel-name`"),
            text="Missing channel",
        )
        return

    channel_ref = parts[1]
    channel_match = re.search(r"<#([A-Z0-9]+)\|?([^>]*)>", channel_ref)

    if channel_match:
        channel_id = channel_match.group(1)
        channel_name = channel_match.group(2) or "channel"
    else:
        channel_name = channel_ref.strip("#").strip()
        channel_id = _lookup_channel_id(channel_name, client)
        if not channel_id:
            respond(
                blocks=BlockKitUI.error_message(
                    f"Could not find channel `#{channel_name}`."
                ),
                text="Channel not found",
            )
            return

    respond(text=f"🔭 Analyzing team in #{channel_name}...")

    messages = rts.search_recent_activity(channel_id)
    team_data = team_analyzer.analyze_team(channel_name, messages)

    blocks = BlockKitUI.team_report_card(channel_name, team_data)
    respond(blocks=blocks, text=f"Team report for #{channel_name}")


def _handle_trends(parts: list, respond, trend_tracker):
    """Handle /slackscope trends — show health score trends."""
    all_latest = trend_tracker.get_all_latest()

    if not all_latest:
        respond(
            blocks=BlockKitUI.error_message(
                "No trend data yet. Run `/slackscope health #channel` or `/slackscope report` first to start tracking."
            ),
            text="No trends",
        )
        return

    blocks = BlockKitUI.trends_card(all_latest, trend_tracker)
    respond(blocks=blocks, text="SlackScope Trends")
