"""
Real-Time Search (RTS) API Wrapper
Uses Slack's assistant.search.context endpoint to query live workspace data.
This is one of the 3 required technologies for the hackathon.
"""

import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class RTSSearch:
    """Wrapper around Slack's Real-Time Search API."""

    def __init__(self, client: WebClient):
        self.client = client

    def search_channel_context(self, query: str, channel_id: str | None = None) -> list[dict]:
        """
        Search workspace using RTS API for AI-relevant context.

        Args:
            query: Natural language search query
            channel_id: Optional channel to scope search to

        Returns:
            List of message dicts with text, user, timestamp, channel
        """
        try:
            # assistant.search.context is the RTS API endpoint
            # It's designed specifically for AI agents to get grounded context
            params = {"query": query}
            if channel_id:
                params["channel_id"] = channel_id

            response = self.client.api_call(
                "assistant.search.context",
                params=params,
            )

            if not response.get("ok"):
                logger.warning(f"RTS search failed: {response.get('error', 'unknown')}")
                # Fallback to standard search.messages if RTS not available
                return self._fallback_search(query, channel_id)

            messages = response.get("messages", [])
            return self._normalize_messages(messages)

        except SlackApiError as e:
            logger.warning(f"RTS API error: {e.response['error']}. Falling back to search.messages")
            return self._fallback_search(query, channel_id)

    def _fallback_search(self, query: str, channel_id: str | None = None) -> list[dict]:
        """
        Fallback to search.messages when RTS API is unavailable.
        Uses standard Slack search with channel scoping.
        """
        try:
            search_query = query
            if channel_id:
                search_query = f"in:<#{channel_id}> {query}"

            response = self.client.search_messages(
                query=search_query,
                count=20,
                sort="timestamp",
                sort_dir="desc",
            )

            matches = response.get("messages", {}).get("matches", [])
            return self._normalize_messages(matches)

        except SlackApiError as e:
            logger.error(f"Fallback search also failed: {e.response['error']}")
            return []

    def search_blockers(self, channel_id: str) -> list[dict]:
        """Search for blocker-related messages in a channel."""
        blocker_queries = [
            "blocked",
            "blocker",
            "stuck",
            "waiting on",
            "dependency",
            "can't proceed",
            "help needed",
            "urgent",
        ]
        all_results = []
        for q in blocker_queries:
            results = self.search_channel_context(q, channel_id)
            all_results.extend(results)

        # Deduplicate by timestamp
        seen = set()
        unique = []
        for msg in all_results:
            if msg["ts"] not in seen:
                seen.add(msg["ts"])
                unique.append(msg)

        return unique

    def search_recent_activity(self, channel_id: str) -> list[dict]:
        """Get recent messages from a channel for health analysis."""
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=50,
            )
            messages = response.get("messages", [])
            return self._normalize_messages(messages)

        except SlackApiError as e:
            logger.error(f"Failed to get channel history: {e.response['error']}")
            return []

    def get_channel_info(self, channel_id: str) -> dict | None:
        """Get channel name and metadata."""
        try:
            response = self.client.conversations_info(channel=channel_id)
            channel = response.get("channel", {})
            return {
                "id": channel.get("id"),
                "name": channel.get("name", "unknown"),
                "topic": channel.get("topic", {}).get("value", ""),
                "purpose": channel.get("purpose", {}).get("value", ""),
                "num_members": channel.get("num_members", 0),
            }
        except SlackApiError as e:
            logger.error(f"Failed to get channel info: {e.response['error']}")
            return None

    def _normalize_messages(self, messages: list) -> list[dict]:
        """Normalize message format from different API responses."""
        normalized = []
        for msg in messages:
            normalized.append({
                "text": msg.get("text", ""),
                "user": msg.get("user", msg.get("username", "unknown")),
                "ts": msg.get("ts", ""),
                "channel": msg.get("channel", {}).get("id", "") if isinstance(msg.get("channel"), dict) else msg.get("channel", ""),
                "type": msg.get("type", "message"),
            })
        return normalized
