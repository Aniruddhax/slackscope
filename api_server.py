"""
SlackScope Dashboard API Server
Serves the web dashboard and provides REST API endpoints.

Usage:
    python api_server.py
    Open http://localhost:5555 in browser
"""

import json
import logging
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from collections import Counter

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from slack_sdk import WebClient
from services.rts_search import RTSSearch
from services.trend_tracker import TrendTracker
from services.smart_alerts import SmartAlertEngine
from agents.health_analyzer import HealthAnalyzer
from agents.team_analyzer import TeamAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dashboard")

# Initialize services
client = WebClient(token=Config.SLACK_BOT_TOKEN)
rts = RTSSearch(client)
analyzer = HealthAnalyzer()
team_analyzer = TeamAnalyzer()
trend_tracker = TrendTracker()
alert_engine = SmartAlertEngine(client)

PORT = int(os.getenv("DASHBOARD_PORT", "5555"))
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")


class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler that serves both API endpoints and static dashboard files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path == "/api/health":
            self._json_response(self._get_health())
        elif path == "/api/trends":
            self._json_response(self._get_trends())
        elif path == "/api/team":
            self._json_response(self._get_team())
        elif path == "/api/alerts":
            self._json_response(self._get_alerts())
        else:
            # Serve static files from dashboard/
            super().do_GET()

    def _json_response(self, data: dict, status: int = 200):
        """Send JSON response with CORS headers."""
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_health(self) -> dict:
        """Get health data for all monitored channels."""
        channels = []

        for channel_id in Config.MONITORED_CHANNELS:
            try:
                info = rts.get_channel_info(channel_id)
                if not info:
                    continue

                name = info["name"]
                messages = rts.search_recent_activity(channel_id)
                health_data = analyzer.analyze_channel_health(name, messages)

                # Record trend
                trend_tracker.record_scan(name, health_data, len(messages))

                channels.append({
                    "id": channel_id,
                    "name": name,
                    "score": health_data.get("score", 0),
                    "status": health_data.get("status", "yellow"),
                    "sentiment": health_data.get("sentiment", "neutral"),
                    "activity": health_data.get("activity_level", "unknown"),
                    "blocker_count": len(health_data.get("blockers", [])),
                    "risk_count": len(health_data.get("risks", [])),
                    "summary": health_data.get("summary", ""),
                    "score_change": trend_tracker.get_score_change(name),
                })
            except Exception as e:
                logger.error(f"Health check failed for {channel_id}: {e}")

        return {
            "channels": channels,
            "alert_count": len(alert_engine.get_active_alerts()),
        }

    def _get_trends(self) -> dict:
        """Get historical trend data for all channels."""
        all_channels = trend_tracker.get_all_channels()
        channels_data = {}

        for ch in all_channels:
            entries = trend_tracker.get_trend(ch, limit=20)
            channels_data[ch] = entries

        return {"channels": channels_data}

    def _get_team(self) -> dict:
        """Get team productivity data across all channels."""
        all_contributors = Counter()
        all_activity_hours = {}

        for channel_id in Config.MONITORED_CHANNELS:
            try:
                info = rts.get_channel_info(channel_id)
                if not info:
                    continue

                name = info["name"]
                messages = rts.search_recent_activity(channel_id)

                # Count contributors
                for msg in messages:
                    user = msg.get("user", "unknown")
                    if user != "unknown":
                        all_contributors[user] += 1

                # Activity hours
                team_data = team_analyzer._compute_activity_hours(messages)
                all_activity_hours[name] = team_data

            except Exception as e:
                logger.error(f"Team data failed for {channel_id}: {e}")

        leaderboard = [
            {"user": user, "count": count}
            for user, count in all_contributors.most_common(10)
        ]

        return {
            "leaderboard": leaderboard,
            "activity_hours": all_activity_hours,
        }

    def _get_alerts(self) -> dict:
        """Get active smart alerts."""
        return {"alerts": alert_engine.get_active_alerts()}

    def log_message(self, format, *args):
        """Suppress default request logging for cleaner output."""
        if "/api/" in str(args):
            return  # Don't log API calls
        super().log_message(format, *args)


def main():
    print(f"🔭 SlackScope Dashboard")
    print(f"=" * 40)

    if not Config.validate():
        print("\\n⚠️ Fix config issues first.")
        sys.exit(1)

    print(f"✅ Config validated")
    print(f"📡 Monitoring {len(Config.MONITORED_CHANNELS)} channels")
    print(f"\\n🌐 Dashboard: http://localhost:{PORT}")
    print(f"📊 API: http://localhost:{PORT}/api/health")
    print(f"\\nPress Ctrl+C to stop.\\n")

    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n👋 Dashboard shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
