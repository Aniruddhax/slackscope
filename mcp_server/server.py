"""
MCP Server for SlackScope
Exposes SlackScope tools via Model Context Protocol.
This is one of the 3 required technologies for the hackathon.

Run separately: python -m mcp_server.server
"""

import os
import sys
import logging

# Add parent dir to path so imports work when running standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from config import Config
from slack_sdk import WebClient
from services.rts_search import RTSSearch
from agents.health_analyzer import HealthAnalyzer
from agents.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    "SlackScope",
    description="AI Project Health Dashboard for Slack. Monitors channels, detects blockers, generates health reports.",
)

# Lazy-initialized shared instances
_client = None
_rts = None
_analyzer = None


def _get_services():
    """Lazily initialize Slack client and services."""
    global _client, _rts, _analyzer
    if _client is None:
        Config.validate()
        _client = WebClient(token=Config.SLACK_BOT_TOKEN)
        _rts = RTSSearch(_client)
        _analyzer = HealthAnalyzer()
    return _client, _rts, _analyzer


@mcp.tool()
def get_project_health(channel_name: str) -> dict:
    """
    Get the health score and analysis for a Slack project channel.

    Args:
        channel_name: Name of the Slack channel (without #)

    Returns:
        Health analysis with score (0-100), status, blockers, risks, and recommendations.
    """
    client, rts, analyzer = _get_services()

    # Find channel by name
    channel_id = _resolve_channel(client, channel_name)
    if not channel_id:
        return {"error": f"Channel #{channel_name} not found"}

    messages = rts.search_recent_activity(channel_id)
    health_data = analyzer.analyze_channel_health(channel_name, messages)

    return health_data


@mcp.tool()
def get_blockers(channel_name: str) -> list[dict]:
    """
    Get all blockers detected in a Slack project channel.

    Args:
        channel_name: Name of the Slack channel (without #)

    Returns:
        List of blockers with description, severity, and who mentioned them.
    """
    client, rts, analyzer = _get_services()

    channel_id = _resolve_channel(client, channel_name)
    if not channel_id:
        return [{"error": f"Channel #{channel_name} not found"}]

    messages = rts.search_recent_activity(channel_id)
    health_data = analyzer.analyze_channel_health(channel_name, messages)

    return health_data.get("blockers", [])


@mcp.tool()
def search_project_context(query: str, channel_name: str | None = None) -> list[dict]:
    """
    Search Slack workspace for project-related context using Real-Time Search.

    Args:
        query: Natural language search query
        channel_name: Optional channel to scope search to

    Returns:
        List of relevant messages with user, text, and timestamp.
    """
    client, rts, _ = _get_services()

    channel_id = None
    if channel_name:
        channel_id = _resolve_channel(client, channel_name)

    results = rts.search_channel_context(query, channel_id)
    return results[:20]  # Cap results


@mcp.tool()
def get_daily_report() -> str:
    """
    Generate a daily health report across all monitored channels.

    Returns:
        Formatted text report summarizing health of all monitored projects.
    """
    client, rts, analyzer = _get_services()

    monitored = Config.MONITORED_CHANNELS
    if not monitored:
        return "No channels configured for monitoring. Set MONITORED_CHANNELS in .env"

    reports = []
    for channel_id in monitored:
        info = rts.get_channel_info(channel_id)
        name = info["name"] if info else channel_id

        messages = rts.search_recent_activity(channel_id)
        health_data = analyzer.analyze_channel_health(name, messages)
        reports.append({"channel_name": name, "health_data": health_data})

    return ReportGenerator.generate_multi_channel_summary(reports)


@mcp.tool()
def ask_about_project(question: str, channel_name: str) -> str:
    """
    Ask a natural language question about a project channel.

    Args:
        question: Your question about the project
        channel_name: The channel to analyze

    Returns:
        AI-generated answer based on channel context.
    """
    client, rts, analyzer = _get_services()

    channel_id = _resolve_channel(client, channel_name)
    if not channel_id:
        return f"Channel #{channel_name} not found"

    messages = rts.search_recent_activity(channel_id)
    rts_results = rts.search_channel_context(question, channel_id)

    # Merge
    seen = set()
    all_msgs = []
    for m in messages + rts_results:
        if m["ts"] not in seen:
            seen.add(m["ts"])
            all_msgs.append(m)

    return analyzer.answer_question(question, all_msgs, channel_name)


def _resolve_channel(client: WebClient, channel_name: str) -> str | None:
    """Find channel ID from name."""
    try:
        resp = client.conversations_list(types="public_channel", limit=200)
        for ch in resp.get("channels", []):
            if ch.get("name") == channel_name:
                return ch["id"]
    except Exception as e:
        logger.error(f"Channel resolution failed: {e}")
    return None


if __name__ == "__main__":
    print("🔭 Starting SlackScope MCP Server...")
    mcp.run()
