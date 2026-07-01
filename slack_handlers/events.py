"""
Slack Event Handlers
Handles @mentions and message events — the main conversational interface.
"""

import re
import logging
from slack_bolt import App
from services.rts_search import RTSSearch
from agents.health_analyzer import HealthAnalyzer
from ui.blocks import BlockKitUI

logger = logging.getLogger(__name__)


def register_events(app: App):
    """Register all event handlers on the Bolt app."""

    rts = RTSSearch(app.client)
    analyzer = HealthAnalyzer()

    @app.event("app_mention")
    def handle_mention(event, say, client):
        """
        Handle when someone @mentions SlackScope.
        Parse their question and respond with AI analysis.
        """
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")

        # Remove the bot mention from text
        clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        if not clean_text:
            say(blocks=BlockKitUI.help_message(), text="SlackScope help")
            return

        logger.info(f"Mention from {user}: {clean_text}")

        # Check if asking about a specific channel
        channel_match = re.search(r"<#([A-Z0-9]+)\|([^>]+)>", text)

        if channel_match:
            target_channel_id = channel_match.group(1)
            target_channel_name = channel_match.group(2)
        else:
            # Default to current channel
            target_channel_id = channel
            info = rts.get_channel_info(channel)
            target_channel_name = info["name"] if info else "this-channel"

        # Check if this is a health check request
        health_keywords = ["health", "status", "how is", "how's", "report", "dashboard"]
        is_health_check = any(kw in clean_text.lower() for kw in health_keywords)

        if is_health_check:
            # Full health report
            say(text=f"🔭 Analyzing #{target_channel_name}... one moment!")

            messages = rts.search_recent_activity(target_channel_id)
            rts_results = rts.search_channel_context(
                f"project updates blockers progress", target_channel_id
            )
            all_messages = _merge_messages(messages, rts_results)

            health_data = analyzer.analyze_channel_health(target_channel_name, all_messages)
            blocks = BlockKitUI.health_report_card(target_channel_name, health_data)
            say(blocks=blocks, text=f"Health report for #{target_channel_name}")

        else:
            # Q&A mode — answer arbitrary question
            say(text=f"🔭 Looking into that for #{target_channel_name}...")

            # Use RTS to search for relevant context
            rts_results = rts.search_channel_context(clean_text, target_channel_id)
            recent = rts.search_recent_activity(target_channel_id)
            all_messages = _merge_messages(recent, rts_results)

            answer = analyzer.answer_question(clean_text, all_messages, target_channel_name)
            blocks = BlockKitUI.question_response(clean_text, answer, target_channel_name)
            say(blocks=blocks, text=answer)

    @app.event("message")
    def handle_message(event, logger):
        """
        Handle regular messages — currently just logs.
        Could be extended for passive monitoring.
        """
        # We don't actively respond to every message
        # This handler prevents "unhandled event" warnings
        pass


def _merge_messages(list1: list[dict], list2: list[dict]) -> list[dict]:
    """Merge two message lists, deduplicating by timestamp."""
    seen = set()
    merged = []
    for msg in list1 + list2:
        ts = msg.get("ts", "")
        if ts not in seen:
            seen.add(ts)
            merged.append(msg)
    return merged
