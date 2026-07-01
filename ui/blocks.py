"""
Block Kit Message Builders
Creates rich, interactive Slack messages using Block Kit.
This is key to the "Design/UX" judging criteria.
"""

from datetime import datetime, timezone


class BlockKitUI:
    """Builds beautiful Block Kit messages for SlackScope."""

    @staticmethod
    def health_report_card(channel_name: str, health_data: dict) -> list[dict]:
        """
        Build a rich health report card for a single channel.

        Returns:
            List of Block Kit blocks
        """
        score = health_data.get("score", 0)
        status = health_data.get("status", "yellow")
        summary = health_data.get("summary", "No analysis available.")
        sentiment = health_data.get("sentiment", "neutral")
        activity = health_data.get("activity_level", "unknown")

        # Status styling
        status_config = {
            "green": {"emoji": "🟢", "color": "#36a64f", "label": "Healthy"},
            "yellow": {"emoji": "🟡", "color": "#daa520", "label": "Needs Attention"},
            "red": {"emoji": "🔴", "color": "#cc0000", "label": "Critical"},
        }
        cfg = status_config.get(status, status_config["yellow"])

        # Build score bar (visual representation)
        filled = score // 10
        empty = 10 - filled
        score_bar = "█" * filled + "░" * empty

        blocks = [
            # Header
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔭 SlackScope Health Report — #{channel_name}",
                    "emoji": True,
                },
            },
            # Score section
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Health Score*\n{cfg['emoji']} *{score}/100* {cfg['label']}\n`{score_bar}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Metrics*\n💬 Sentiment: {sentiment.title()}\n📊 Activity: {activity.title()}",
                    },
                ],
            },
            {"type": "divider"},
            # Summary
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary*\n{summary}",
                },
            },
        ]

        # Blockers section
        blockers = health_data.get("blockers", [])
        if blockers:
            blocker_lines = []
            for b in blockers[:5]:  # Cap at 5
                severity = b.get("severity", "medium")
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                blocker_lines.append(f"{severity_emoji} {b.get('description', 'Unknown')}")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚧 Blockers ({len(blockers)})*\n" + "\n".join(blocker_lines),
                },
            })

        # Risks section
        risks = health_data.get("risks", [])
        if risks:
            risk_lines = [f"• {r.get('description', 'Unknown')}" for r in risks[:5]]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ Risks ({len(risks)})*\n" + "\n".join(risk_lines),
                },
            })

        # Highlights section
        highlights = health_data.get("highlights", [])
        if highlights:
            highlight_lines = [f"• {h}" for h in highlights[:5]]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✨ Highlights*\n" + "\n".join(highlight_lines),
                },
            })

        # Recommendations
        recommendations = health_data.get("recommendations", [])
        if recommendations:
            rec_lines = [f"• {r}" for r in recommendations[:3]]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💡 Recommendations*\n" + "\n".join(rec_lines),
                },
            })

        # Action buttons
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔍 Deep Dive", "emoji": True},
                    "action_id": "deep_dive",
                    "value": channel_name,
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📋 View Blockers", "emoji": True},
                    "action_id": "view_blockers",
                    "value": channel_name,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔇 Snooze", "emoji": True},
                    "action_id": "snooze_channel",
                    "value": channel_name,
                },
            ],
        })

        # Footer with timestamp
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🔭 SlackScope | Generated {now} | `/slackscope help` for commands",
                },
            ],
        })

        return blocks

    @staticmethod
    def daily_dashboard(reports: list[dict]) -> list[dict]:
        """
        Build a multi-channel daily dashboard.

        Args:
            reports: List of {'channel_name': str, 'health_data': dict}

        Returns:
            Block Kit blocks
        """
        status_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

        # Sort worst-first
        sorted_reports = sorted(reports, key=lambda r: r["health_data"].get("score", 0))

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔭 SlackScope Daily Dashboard",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📅 {datetime.now(timezone.utc).strftime('%A, %B %d, %Y')} | {len(reports)} channels monitored",
                    },
                ],
            },
            {"type": "divider"},
        ]

        # Channel rows
        for report in sorted_reports:
            name = report["channel_name"]
            data = report["health_data"]
            score = data.get("score", 0)
            status = data.get("status", "yellow")
            emoji = status_emoji.get(status, "⚪")
            summary = data.get("summary", "")[:100]
            blockers = len(data.get("blockers", []))

            blocker_text = f" | 🚧 {blockers} blocker(s)" if blockers > 0 else ""
            filled = score // 10
            empty = 10 - filled
            bar = "█" * filled + "░" * empty

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *#{name}* — *{score}/100*{blocker_text}\n`{bar}`\n_{summary}_",
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Details", "emoji": True},
                    "action_id": "channel_details",
                    "value": name,
                },
            })

        # Overall stats
        scores = [r["health_data"].get("score", 0) for r in reports]
        avg = sum(scores) // len(scores) if scores else 0
        total_blockers = sum(len(r["health_data"].get("blockers", [])) for r in reports)

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*📈 Avg Health*\n{avg}/100"},
                {"type": "mrkdwn", "text": f"*🚧 Total Blockers*\n{total_blockers}"},
            ],
        })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 _Use `/slackscope health #channel` for a detailed report on any channel_",
                },
            ],
        })

        return blocks

    @staticmethod
    def question_response(question: str, answer: str, channel_name: str) -> list[dict]:
        """Build a response block for Q&A interactions."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔭 *SlackScope* analyzed #{channel_name} to answer your question:",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": answer,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"❓ _{question}_",
                    },
                ],
            },
        ]

    @staticmethod
    def error_message(error_text: str) -> list[dict]:
        """Build an error message block."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *SlackScope Error*\n{error_text}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "_Try `/slackscope help` for usage info_"},
                ],
            },
        ]

    @staticmethod
    def help_message() -> list[dict]:
        """Build the help/usage message."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔭 SlackScope — AI Project Health Dashboard",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Commands:*\n"
                        "• `/slackscope health #channel` — Get health report for a channel\n"
                        "• `/slackscope report` — Trigger daily report now\n"
                        "• `/slackscope configure` — Set monitored channels\n"
                        "• `/slackscope team #channel` — Team productivity insights\n"
                        "• `/slackscope trends` — Health score trends\n"
                        "• `/slackscope help` — Show this message\n"
                        "\n"
                        "*Mention me:*\n"
                        "• `@SlackScope how is #project-alpha going?` — Ask about any project\n"
                        "• `@SlackScope what are the blockers in #backend?` — Find blockers\n"
                        "• `@SlackScope summarize #design-review` — Get channel summary"
                    ),
                },
            },
        ]

    @staticmethod
    def team_report_card(channel_name: str, team_data: dict) -> list[dict]:
        """Build a team productivity report card."""
        stats = team_data.get("message_stats", {})
        collab_score = team_data.get("collaboration_score", 0)
        quality = team_data.get("communication_quality", "fair")
        summary = team_data.get("team_dynamics_summary", "Insufficient data.")
        hours = team_data.get("activity_hours", [0] * 24)

        # Collaboration score bar
        filled = collab_score // 10
        empty = 10 - filled
        score_bar = "█" * filled + "░" * empty

        quality_emoji = {
            "excellent": "🌟", "good": "✅", "fair": "🟡", "poor": "🔴"
        }.get(quality, "⚪")

        # Peak hours
        if any(hours):
            peak_hour = hours.index(max(hours))
            peak_str = f"{peak_hour:02d}:00 UTC"
        else:
            peak_str = "No data"

        # Top contributors
        top = stats.get("top_contributors", [])
        contrib_lines = [f"• <@{c['user']}>: {c['count']} msgs" for c in top[:3]]
        contrib_text = "\n".join(contrib_lines) if contrib_lines else "No data"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"👥 Team Insights — #{channel_name}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Collaboration Score*\n`{score_bar}` *{collab_score}/100*",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Communication*\n{quality_emoji} {quality.title()}",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*📊 Stats*\n💬 {stats.get('total_messages', 0)} messages\n👤 {stats.get('unique_users', 0)} participants\n❓ {stats.get('questions_count', 0)} questions",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*⏰ Peak Activity*\n{peak_str}\n\n*🏆 Top Contributors*\n{contrib_text}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Team Dynamics*\n{summary}",
                },
            },
        ]

        # Unresolved questions
        unresolved = team_data.get("unresolved_questions", [])
        if unresolved:
            q_lines = [f"• {q.get('question', '?')}" for q in unresolved[:3]]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*❓ Unresolved Questions ({len(unresolved)})*\n" + "\n".join(q_lines),
                },
            })

        # Suggestions
        suggestions = team_data.get("improvement_suggestions", [])
        if suggestions:
            s_lines = [f"• {s}" for s in suggestions[:3]]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💡 Suggestions*\n" + "\n".join(s_lines),
                },
            })

        # Footer
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"👥 SlackScope Team Insights | {now}"}],
        })

        return blocks

    @staticmethod
    def trends_card(all_latest: dict, trend_tracker) -> list[dict]:
        """Build a trends overview card."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📈 SlackScope Health Trends",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Tracking {len(all_latest)} channels",
                    },
                ],
            },
            {"type": "divider"},
        ]

        status_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

        for channel, latest in all_latest.items():
            score = latest.get("score", 0)
            status = latest.get("status", "yellow")
            emoji = status_emoji.get(status, "⚪")
            sentiment = latest.get("sentiment", "neutral")
            change = trend_tracker.get_score_change(channel)

            if change > 0:
                trend_icon = f"📈 +{change}"
            elif change < 0:
                trend_icon = f"📉 {change}"
            else:
                trend_icon = "➡️ 0"

            filled = score // 10
            bar = "█" * filled + "░" * (10 - filled)

            history = trend_tracker.get_trend(channel, limit=5)
            history_scores = [str(e.get('score', '?')) for e in history]
            history_str = " → ".join(history_scores) if history_scores else "No history"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *#{channel}* — *{score}/100* {trend_icon}\n"
                        f"`{bar}` | Sentiment: {sentiment}\n"
                        f"History: {history_str}"
                    ),
                },
            })

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📈 SlackScope Trends | {now} | Run `/slackscope health #channel` to update"}],
        })

        return blocks
