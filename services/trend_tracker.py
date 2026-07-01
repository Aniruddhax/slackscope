"""
Trend Tracker Service
Persists health scores over time for trend analysis and dashboard charts.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
TRENDS_FILE = DATA_DIR / "trends.json"


class TrendTracker:
    """Tracks channel health scores over time."""

    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._trends = self._load()

    def _load(self) -> dict:
        """Load trends from disk."""
        if TRENDS_FILE.exists():
            try:
                with open(TRENDS_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Corrupted trends file, starting fresh")
        return {}

    def _save(self):
        """Persist trends to disk."""
        try:
            with open(TRENDS_FILE, "w") as f:
                json.dump(self._trends, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save trends: {e}")

    def record_scan(self, channel_name: str, health_data: dict, message_count: int = 0):
        """
        Record a health scan result for trend tracking.

        Args:
            channel_name: Channel that was scanned
            health_data: Health analysis results from HealthAnalyzer
            message_count: Number of messages analyzed
        """
        if channel_name not in self._trends:
            self._trends[channel_name] = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": health_data.get("score", 0),
            "status": health_data.get("status", "unknown"),
            "sentiment": health_data.get("sentiment", "neutral"),
            "activity_level": health_data.get("activity_level", "unknown"),
            "blocker_count": len(health_data.get("blockers", [])),
            "risk_count": len(health_data.get("risks", [])),
            "message_count": message_count,
        }

        self._trends[channel_name].append(entry)

        # Keep last 30 days of data (max ~720 entries at 1 scan/hour)
        self._trends[channel_name] = self._trends[channel_name][-720:]

        self._save()
        logger.info(f"Recorded trend for #{channel_name}: score={entry['score']}")

    def get_trend(self, channel_name: str, limit: int = 50) -> list[dict]:
        """Get historical trend data for a channel."""
        return self._trends.get(channel_name, [])[-limit:]

    def get_all_latest(self) -> dict[str, dict]:
        """Get the latest scan result for each channel."""
        latest = {}
        for channel, entries in self._trends.items():
            if entries:
                latest[channel] = entries[-1]
        return latest

    def get_score_change(self, channel_name: str) -> int:
        """Get score change between last two scans. Positive = improving."""
        entries = self._trends.get(channel_name, [])
        if len(entries) < 2:
            return 0
        return entries[-1]["score"] - entries[-2]["score"]

    def get_sentiment_history(self, channel_name: str, limit: int = 20) -> list[dict]:
        """Get sentiment over time for charting."""
        entries = self.get_trend(channel_name, limit)
        return [
            {
                "timestamp": e["timestamp"],
                "sentiment": e["sentiment"],
                "score": e["score"],
            }
            for e in entries
        ]

    def get_all_channels(self) -> list[str]:
        """Get list of all tracked channels."""
        return list(self._trends.keys())
