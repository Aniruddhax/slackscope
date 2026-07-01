"""
Smart Alerts Service
Proactive notifications when channels go unhealthy.
DMs team leads automatically based on configurable rules.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from slack_sdk import WebClient

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
ALERTS_FILE = DATA_DIR / "alerts.json"

# Cooldown: max 1 alert per channel per 6 hours
COOLDOWN_HOURS = 6


class SmartAlertEngine:
    """Proactive alert system for unhealthy channels."""

    def __init__(self, client: WebClient):
        self.client = client
        DATA_DIR.mkdir(exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> dict:
        """Load alert state from disk."""
        if ALERTS_FILE.exists():
            try:
                with open(ALERTS_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"sent_alerts": {}, "active_alerts": []}

    def _save_state(self):
        """Persist alert state."""
        try:
            with open(ALERTS_FILE, "w") as f:
                json.dump(self._state, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save alert state: {e}")

    def evaluate_channel(self, channel_name: str, channel_id: str, health_data: dict, previous_score: int | None = None):
        """
        Evaluate a channel's health and send alerts if needed.

        Args:
            channel_name: Name of the channel
            channel_id: Slack channel ID
            health_data: Current health analysis
            previous_score: Score from last scan (for delta detection)
        """
        score = health_data.get("score", 100)
        blockers = health_data.get("blockers", [])
        sentiment = health_data.get("sentiment", "neutral")
        activity = health_data.get("activity_level", "moderate")

        alerts_to_send = []

        # Rule 1: Health drops below 40 → Critical alert
        if score < 40:
            alerts_to_send.append({
                "type": "critical_health",
                "emoji": "🔴",
                "title": f"Critical Health Alert — #{channel_name}",
                "message": (
                    f"Health score dropped to *{score}/100* (Critical).\n"
                    f"Sentiment: {sentiment} | Activity: {activity}\n"
                    f"Summary: {health_data.get('summary', 'N/A')}"
                ),
            })

        # Rule 2: 3+ blockers detected
        if len(blockers) >= 3:
            blocker_list = "\n".join(
                f"  • {b.get('description', 'Unknown')} ({b.get('severity', 'medium')})"
                for b in blockers[:5]
            )
            alerts_to_send.append({
                "type": "blocker_alert",
                "emoji": "🚧",
                "title": f"Multiple Blockers — #{channel_name}",
                "message": f"*{len(blockers)} blockers* detected:\n{blocker_list}",
            })

        # Rule 3: Big score drop (>20 points)
        if previous_score is not None and (previous_score - score) > 20:
            alerts_to_send.append({
                "type": "score_drop",
                "emoji": "📉",
                "title": f"Health Score Drop — #{channel_name}",
                "message": f"Score dropped *{previous_score - score} points* ({previous_score} → {score}).",
            })

        # Rule 4: Negative sentiment
        if sentiment == "negative" and score < 60:
            alerts_to_send.append({
                "type": "negative_sentiment",
                "emoji": "😟",
                "title": f"Negative Sentiment Detected — #{channel_name}",
                "message": f"Team morale may need attention. Sentiment: *{sentiment}*, Score: *{score}/100*.",
            })

        # Rule 5: Channel inactive
        if activity == "inactive":
            alerts_to_send.append({
                "type": "inactive",
                "emoji": "💤",
                "title": f"Channel Inactive — #{channel_name}",
                "message": f"No recent activity detected in #{channel_name}. Project may need a check-in.",
            })

        # Send alerts with cooldown
        for alert in alerts_to_send:
            self._send_alert(channel_name, channel_id, alert)

    def _send_alert(self, channel_name: str, channel_id: str, alert: dict):
        """Send alert DM to channel, respecting cooldown."""
        alert_key = f"{channel_name}:{alert['type']}"
        now = datetime.now(timezone.utc)

        # Check cooldown
        last_sent = self._state["sent_alerts"].get(alert_key)
        if last_sent:
            last_time = datetime.fromisoformat(last_sent)
            if now - last_time < timedelta(hours=COOLDOWN_HOURS):
                logger.debug(f"Alert {alert_key} in cooldown, skipping")
                return

        # Post alert to the channel itself
        try:
            self.client.chat_postMessage(
                channel=channel_id,
                text=f"{alert['emoji']} *{alert['title']}*\n\n{alert['message']}\n\n_🔭 SlackScope Smart Alert | Use `/slackscope health {channel_name}` for details_",
            )

            # Update state
            self._state["sent_alerts"][alert_key] = now.isoformat()
            self._state["active_alerts"].append({
                "channel": channel_name,
                "type": alert["type"],
                "title": alert["title"],
                "message": alert["message"],
                "timestamp": now.isoformat(),
            })
            # Keep last 100 alerts
            self._state["active_alerts"] = self._state["active_alerts"][-100:]
            self._save_state()

            logger.info(f"Smart alert sent: {alert['title']}")

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def get_active_alerts(self, limit: int = 20) -> list[dict]:
        """Get recent active alerts."""
        return self._state.get("active_alerts", [])[-limit:]

    def clear_alerts(self, channel_name: str):
        """Clear active alerts for a channel."""
        self._state["active_alerts"] = [
            a for a in self._state["active_alerts"]
            if a["channel"] != channel_name
        ]
        self._save_state()
