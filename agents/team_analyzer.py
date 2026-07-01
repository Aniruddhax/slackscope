"""
Team Productivity Analyzer
Extracts team metrics from channel messages using LLM + heuristics.
"""

import logging
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

TEAM_ANALYSIS_PROMPT = """You are SlackScope's Team Productivity Analyzer. Given messages from a Slack channel, analyze team dynamics and return a JSON object:

{
  "collaboration_score": <integer 0-100>,
  "communication_quality": "<excellent|good|fair|poor>",
  "unresolved_questions": [
    {"question": "<the question>", "asked_by": "<user>"}
  ],
  "key_contributors": [
    {"user": "<user_id>", "role": "<what they do based on messages>"}
  ],
  "team_dynamics_summary": "<2-3 sentence summary of how the team works together>",
  "improvement_suggestions": [
    "<actionable suggestion>"
  ]
}

Focus on collaboration patterns, responsiveness, and knowledge sharing. Be specific."""


class TeamAnalyzer:
    """Analyzes team productivity and collaboration patterns."""

    def __init__(self):
        self.client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url=Config.LLM_BASE_URL,
        )
        self.model = Config.LLM_MODEL

    def analyze_team(self, channel_name: str, messages: list[dict]) -> dict:
        """
        Full team productivity analysis.

        Returns dict with message_stats, response_times, collaboration metrics.
        """
        # Heuristic analysis (fast, no LLM)
        stats = self._compute_message_stats(messages)
        activity_hours = self._compute_activity_hours(messages)

        # LLM analysis (deeper insights)
        llm_insights = self._llm_team_analysis(channel_name, messages)

        return {
            "channel_name": channel_name,
            "message_stats": stats,
            "activity_hours": activity_hours,
            "collaboration_score": llm_insights.get("collaboration_score", 50),
            "communication_quality": llm_insights.get("communication_quality", "fair"),
            "unresolved_questions": llm_insights.get("unresolved_questions", []),
            "key_contributors": llm_insights.get("key_contributors", []),
            "team_dynamics_summary": llm_insights.get("team_dynamics_summary", "Insufficient data."),
            "improvement_suggestions": llm_insights.get("improvement_suggestions", []),
        }

    def _compute_message_stats(self, messages: list[dict]) -> dict:
        """Compute basic message statistics."""
        if not messages:
            return {
                "total_messages": 0,
                "unique_users": 0,
                "top_contributors": [],
                "avg_message_length": 0,
                "questions_count": 0,
            }

        user_counts = Counter(m.get("user", "unknown") for m in messages)
        texts = [m.get("text", "") for m in messages]
        questions = sum(1 for t in texts if "?" in t)

        top = [
            {"user": user, "count": count}
            for user, count in user_counts.most_common(5)
        ]

        avg_len = sum(len(t) for t in texts) // max(len(texts), 1)

        return {
            "total_messages": len(messages),
            "unique_users": len(user_counts),
            "top_contributors": top,
            "avg_message_length": avg_len,
            "questions_count": questions,
        }

    def _compute_activity_hours(self, messages: list[dict]) -> list[int]:
        """
        Compute message counts per hour (0-23).
        Returns list of 24 integers.
        """
        hours = [0] * 24
        for msg in messages:
            ts = msg.get("ts", "")
            if ts:
                try:
                    dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                    hours[dt.hour] += 1
                except (ValueError, OSError):
                    pass
        return hours

    def _llm_team_analysis(self, channel_name: str, messages: list[dict]) -> dict:
        """Use LLM for deeper team dynamics analysis."""
        if not messages:
            return {}

        formatted = self._format_for_llm(channel_name, messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": TEAM_ANALYSIS_PROMPT},
                    {"role": "user", "content": formatted},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=800,
            )
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Team LLM analysis failed: {e}")
            return {}

    def _format_for_llm(self, channel_name: str, messages: list[dict]) -> str:
        """Format messages for LLM input."""
        lines = [f"Channel: #{channel_name}", f"Messages: {len(messages)}", "---"]
        for msg in messages[:40]:
            user = msg.get("user", "unknown")
            text = msg.get("text", "")
            if text.strip():
                lines.append(f"[{user}]: {text}")
        return "\n".join(lines)
