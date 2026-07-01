"""
Channel Monitor Service
Scans configured channels and builds health reports.
Now with trend tracking and smart alerts integration.
"""

import logging
from slack_sdk import WebClient
from services.rts_search import RTSSearch
from agents.health_analyzer import HealthAnalyzer
from services.trend_tracker import TrendTracker
from services.smart_alerts import SmartAlertEngine
from config import Config

logger = logging.getLogger(__name__)


class ChannelMonitor:
    """Monitors configured channels and generates health reports."""

    def __init__(self, client: WebClient):
        self.client = client
        self.rts = RTSSearch(client)
        self.analyzer = HealthAnalyzer()
        self.trend_tracker = TrendTracker()
        self.alert_engine = SmartAlertEngine(client)

    def scan_all_channels(self) -> list[dict]:
        """
        Scan all monitored channels and return health reports.
        Also records trends and evaluates smart alerts.

        Returns:
            List of {'channel_name': str, 'channel_id': str, 'health_data': dict}
        """
        reports = []

        for channel_id in Config.MONITORED_CHANNELS:
            try:
                report = self.scan_channel(channel_id)
                if report:
                    reports.append(report)
            except Exception as e:
                logger.error(f"Failed to scan channel {channel_id}: {e}")
                reports.append({
                    "channel_name": channel_id,
                    "channel_id": channel_id,
                    "health_data": {
                        "score": 0,
                        "status": "red",
                        "summary": f"Error scanning channel: {str(e)}",
                        "blockers": [],
                        "risks": [{"description": "Channel scan failed", "likelihood": "high"}],
                        "highlights": [],
                        "sentiment": "unknown",
                        "activity_level": "unknown",
                        "recommendations": ["Check channel permissions"],
                    },
                })

        return reports

    def scan_channel(self, channel_id: str) -> dict | None:
        """
        Scan a single channel and return its health report.
        Records trend data and evaluates smart alerts.
        """
        # Get channel info
        info = self.rts.get_channel_info(channel_id)
        if not info:
            logger.warning(f"Could not get info for channel {channel_id}")
            return None

        channel_name = info["name"]

        # Get recent messages
        messages = self.rts.search_recent_activity(channel_id)

        # Also do RTS search for deeper context
        rts_results = self.rts.search_channel_context(
            "blockers progress updates risks milestones", channel_id
        )

        # Merge and deduplicate
        seen = set()
        all_messages = []
        for msg in messages + rts_results:
            ts = msg.get("ts", "")
            if ts not in seen:
                seen.add(ts)
                all_messages.append(msg)

        # Analyze
        health_data = self.analyzer.analyze_channel_health(channel_name, all_messages)

        # Record trend
        previous_score = None
        trend_entries = self.trend_tracker.get_trend(channel_name, limit=1)
        if trend_entries:
            previous_score = trend_entries[-1].get("score")

        self.trend_tracker.record_scan(channel_name, health_data, len(all_messages))

        # Evaluate smart alerts
        self.alert_engine.evaluate_channel(
            channel_name, channel_id, health_data, previous_score
        )

        return {
            "channel_name": channel_name,
            "channel_id": channel_id,
            "health_data": health_data,
        }

