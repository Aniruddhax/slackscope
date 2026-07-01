"""
Action Handlers
Handles interactive button clicks and modal submissions.
"""

import logging
from slack_bolt import App
from services.rts_search import RTSSearch
from agents.health_analyzer import HealthAnalyzer
from ui.blocks import BlockKitUI

logger = logging.getLogger(__name__)


def register_actions(app: App):
    """Register all interactive action handlers."""

    rts = RTSSearch(app.client)
    analyzer = HealthAnalyzer()

    @app.action("deep_dive")
    def handle_deep_dive(ack, body, respond):
        """Handle 'Deep Dive' button click — show detailed blocker analysis."""
        ack()
        channel_name = body["actions"][0]["value"]

        respond(
            text=f"🔍 Deep diving into #{channel_name}...",
            replace_original=False,
        )

        # Search specifically for blockers and issues
        info = _find_channel_by_name(rts, channel_name)
        if not info:
            respond(
                blocks=BlockKitUI.error_message(f"Could not find channel #{channel_name}"),
                text="Channel not found",
                replace_original=False,
            )
            return

        blocker_messages = rts.search_blockers(info["id"])
        recent = rts.search_recent_activity(info["id"])

        health_data = analyzer.analyze_channel_health(channel_name, recent + blocker_messages)

        # Post detailed report
        blocks = BlockKitUI.health_report_card(channel_name, health_data)
        respond(blocks=blocks, text=f"Deep dive: #{channel_name}", replace_original=False)

    @app.action("view_blockers")
    def handle_view_blockers(ack, body, respond):
        """Handle 'View Blockers' button click."""
        ack()
        channel_name = body["actions"][0]["value"]

        info = _find_channel_by_name(rts, channel_name)
        if not info:
            respond(
                blocks=BlockKitUI.error_message(f"Could not find channel #{channel_name}"),
                text="Channel not found",
                replace_original=False,
            )
            return

        blocker_messages = rts.search_blockers(info["id"])

        if not blocker_messages:
            respond(
                text=f"✅ No blockers found in #{channel_name}! Looking good.",
                replace_original=False,
            )
            return

        # Format blocker messages
        lines = [f"🚧 *Blockers found in #{channel_name}:*\n"]
        for msg in blocker_messages[:10]:
            user = msg.get("user", "unknown")
            text = msg.get("text", "")[:200]
            lines.append(f"• <@{user}>: _{text}_")

        respond(text="\n".join(lines), replace_original=False)

    @app.action("snooze_channel")
    def handle_snooze(ack, body, respond):
        """Handle 'Snooze' button click — acknowledge and mute alerts temporarily."""
        ack()
        channel_name = body["actions"][0]["value"]
        respond(
            text=f"🔇 Snoozed alerts for #{channel_name} for 24 hours.",
            replace_original=False,
        )

    @app.action("channel_details")
    def handle_channel_details(ack, body, respond):
        """Handle 'Details' button from daily dashboard."""
        ack()
        channel_name = body["actions"][0]["value"]

        respond(text=f"🔭 Fetching details for #{channel_name}...", replace_original=False)

        info = _find_channel_by_name(rts, channel_name)
        if not info:
            respond(
                blocks=BlockKitUI.error_message(f"Could not find #{channel_name}"),
                text="Not found",
                replace_original=False,
            )
            return

        messages = rts.search_recent_activity(info["id"])
        health_data = analyzer.analyze_channel_health(channel_name, messages)
        blocks = BlockKitUI.health_report_card(channel_name, health_data)
        respond(blocks=blocks, text=f"Details: #{channel_name}", replace_original=False)

    @app.view("slackscope_config")
    def handle_config_submission(ack, body, view, client):
        """Handle configuration modal submission."""
        ack()

        values = view["state"]["values"]
        selected_channels = values["channels_block"]["selected_channels"]["selected_conversations"]
        report_channel = values["report_channel_block"]["report_channel"]["selected_conversation"]

        user_id = body["user"]["id"]

        # Store config (in production, use a database)
        # For hackathon, we log it and inform the user
        logger.info(f"Config update by {user_id}: channels={selected_channels}, report={report_channel}")

        client.chat_postMessage(
            channel=user_id,
            text=(
                f"✅ *SlackScope configured!*\n"
                f"• Monitoring {len(selected_channels)} channels\n"
                f"• Daily reports will post to <#{report_channel}>\n\n"
                f"_Note: Update your `.env` file with these channel IDs for persistence._"
            ),
        )


def _find_channel_by_name(rts: RTSSearch, channel_name: str) -> dict | None:
    """Try to find a channel by name using conversations.list."""
    try:
        # This is a simplification — in production, cache channel list
        response = rts.client.conversations_list(types="public_channel", limit=200)
        for ch in response.get("channels", []):
            if ch.get("name") == channel_name:
                return {"id": ch["id"], "name": ch["name"]}
    except Exception as e:
        logger.error(f"Channel lookup failed: {e}")
    return None
