"""
Scheduler Service
Runs daily health reports on a cron schedule using APScheduler.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk import WebClient
from services.channel_monitor import ChannelMonitor
from ui.blocks import BlockKitUI
from config import Config

logger = logging.getLogger(__name__)


class ReportScheduler:
    """Manages scheduled health report generation and posting."""

    def __init__(self, client: WebClient):
        self.client = client
        self.monitor = ChannelMonitor(client)
        self.scheduler = BackgroundScheduler()

    def start(self):
        """Start the daily report schedule."""
        if not Config.MONITORED_CHANNELS:
            logger.info("No channels configured — scheduler not started")
            return

        if not Config.REPORT_CHANNEL:
            logger.warning("No REPORT_CHANNEL configured — scheduler not started")
            return

        # Parse time from config (HH:MM format)
        try:
            hour, minute = Config.DAILY_REPORT_TIME.split(":")
            hour, minute = int(hour), int(minute)
        except ValueError:
            logger.warning(f"Invalid DAILY_REPORT_TIME: {Config.DAILY_REPORT_TIME}. Using 09:00")
            hour, minute = 9, 0

        # Schedule daily report
        self.scheduler.add_job(
            self._run_daily_report,
            "cron",
            hour=hour,
            minute=minute,
            id="daily_health_report",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(f"📅 Daily report scheduled at {hour:02d}:{minute:02d} UTC")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def run_now(self):
        """Trigger a report immediately (for manual /slackscope report)."""
        self._run_daily_report()

    def _run_daily_report(self):
        """Execute the daily report — scan all channels and post dashboard."""
        logger.info("🔭 Running daily health report...")

        try:
            reports = self.monitor.scan_all_channels()

            if not reports:
                logger.warning("No reports generated — no channels to scan")
                return

            # Build and post dashboard
            blocks = BlockKitUI.daily_dashboard(reports)

            self.client.chat_postMessage(
                channel=Config.REPORT_CHANNEL,
                blocks=blocks,
                text="🔭 SlackScope Daily Health Report",
            )

            logger.info(f"✅ Daily report posted to {Config.REPORT_CHANNEL} ({len(reports)} channels)")

        except Exception as e:
            logger.error(f"Daily report failed: {e}")

            # Try to notify about the failure
            try:
                self.client.chat_postMessage(
                    channel=Config.REPORT_CHANNEL,
                    text=f"❌ SlackScope daily report failed: {str(e)}",
                )
            except Exception:
                pass
