"""
AI Health Analyzer
Uses Groq (free, OpenAI-compatible) to analyze channel messages and produce structured health scores.
"""

import json
import logging
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

# System prompt for the health analyzer
HEALTH_ANALYSIS_PROMPT = """You are SlackScope, an AI project health analyst. You analyze Slack channel messages and produce a structured health assessment.

Given a set of recent messages from a project channel, analyze them and return a JSON object with:

{
  "score": <integer 0-100, where 100 = perfectly healthy>,
  "status": "<green|yellow|red>",
  "summary": "<2-3 sentence overview of project health>",
  "blockers": [
    {"description": "<what's blocked>", "severity": "<high|medium|low>", "mentioned_by": "<user or 'unknown'>"}
  ],
  "risks": [
    {"description": "<potential risk>", "likelihood": "<high|medium|low>"}
  ],
  "highlights": [
    "<positive thing happening in the project>"
  ],
  "sentiment": "<positive|neutral|negative|mixed>",
  "activity_level": "<high|moderate|low|inactive>",
  "recommendations": [
    "<actionable suggestion to improve project health>"
  ]
}

Scoring guidelines:
- 80-100 (green): Active, no blockers, positive sentiment
- 50-79 (yellow): Some blockers or risks, moderate activity
- 0-49 (red): Major blockers, negative sentiment, low activity or urgent issues

Be specific and cite actual messages when possible. If there are no messages or very few, note low activity as a risk."""

QUESTION_PROMPT = """You are SlackScope, an AI project health assistant inside Slack. A user asked a question about their project.

Based on the channel messages provided, answer the user's question concisely and helpfully. Reference specific messages or people when relevant. Keep your response under 300 words.

If you can't find relevant information in the messages, say so honestly and suggest what channels or people to check."""


class HealthAnalyzer:
    """LLM-powered project health analysis engine."""

    def __init__(self):
        self.client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url=Config.LLM_BASE_URL,
        )
        self.model = Config.LLM_MODEL

    def analyze_channel_health(self, channel_name: str, messages: list[dict]) -> dict:
        """
        Analyze messages from a channel and return structured health data.

        Args:
            channel_name: Name of the channel being analyzed
            messages: List of message dicts from RTS search

        Returns:
            Health analysis dict with score, blockers, risks, etc.
        """
        if not messages:
            return {
                "score": 30,
                "status": "red",
                "summary": f"No recent activity found in #{channel_name}. This could indicate an inactive or abandoned project.",
                "blockers": [],
                "risks": [{"description": "No recent activity detected", "likelihood": "high"}],
                "highlights": [],
                "sentiment": "neutral",
                "activity_level": "inactive",
                "recommendations": ["Check if this channel is still active", "Reach out to team members"],
            }

        # Format messages for LLM
        formatted = self._format_messages_for_llm(channel_name, messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": HEALTH_ANALYSIS_PROMPT},
                    {"role": "user", "content": formatted},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000,
            )

            result = json.loads(response.choices[0].message.content)

            # Validate and set defaults
            result.setdefault("score", 50)
            result.setdefault("status", self._score_to_status(result["score"]))
            result.setdefault("summary", "Analysis complete.")
            result.setdefault("blockers", [])
            result.setdefault("risks", [])
            result.setdefault("highlights", [])
            result.setdefault("sentiment", "neutral")
            result.setdefault("activity_level", "moderate")
            result.setdefault("recommendations", [])

            return result

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                "score": 50,
                "status": "yellow",
                "summary": f"Unable to fully analyze #{channel_name} due to an error. Partial data available.",
                "blockers": [],
                "risks": [{"description": "Analysis engine error — manual review recommended", "likelihood": "medium"}],
                "highlights": [],
                "sentiment": "unknown",
                "activity_level": "unknown",
                "recommendations": ["Manual review recommended"],
            }

    def answer_question(self, question: str, messages: list[dict], channel_name: str) -> str:
        """
        Answer a user's question about their project based on channel context.

        Args:
            question: User's question text
            messages: Relevant messages from RTS search
            channel_name: Channel name for context

        Returns:
            Natural language answer string
        """
        formatted = self._format_messages_for_llm(channel_name, messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUESTION_PROMPT},
                    {"role": "user", "content": f"Channel: #{channel_name}\n\nQuestion: {question}\n\nRecent messages:\n{formatted}"},
                ],
                temperature=0.5,
                max_tokens=500,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            return f"Sorry, I couldn't analyze the messages right now. Error: {str(e)}"

    def _format_messages_for_llm(self, channel_name: str, messages: list[dict]) -> str:
        """Format messages into a readable string for LLM input."""
        lines = [f"Channel: #{channel_name}", f"Total messages: {len(messages)}", "---"]

        for msg in messages[:50]:  # Cap at 50 messages to stay within token limits
            user = msg.get("user", "unknown")
            text = msg.get("text", "")
            if text.strip():
                lines.append(f"[{user}]: {text}")

        return "\n".join(lines)

    def _score_to_status(self, score: int) -> str:
        """Convert numeric score to status color."""
        if score >= Config.HEALTH_GOOD:
            return "green"
        elif score >= Config.HEALTH_WARNING:
            return "yellow"
        return "red"
