# SlackScope — AI Project Health Dashboard for Slack

> 🏆 Built for the [Slack Agent Builder Challenge](https://slackhack.devpost.com/) hackathon
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/5977c458-e87a-4cc8-b648-eef8f8b75686" />


## What is SlackScope?

SlackScope is an intelligent Slack agent that monitors your project channels and provides real-time health dashboards. It uses AI to detect blockers, analyze team sentiment, and surface risks — so project managers never miss what matters.

## Features

- 🔍 **Smart Channel Scanning** — Uses Slack's Real-Time Search (RTS) API to query conversations
- 🧠 **AI-Powered Analysis** — LLM analyzes messages for blockers, risks, and sentiment
- 📊 **Health Report Cards** — Beautiful Block Kit dashboards with color-coded health scores
- ⏰ **Scheduled Reports** — Daily automated health summaries posted to your channel
- 🔌 **MCP Integration** — Exposes tools via Model Context Protocol for external AI access
- 💬 **Conversational** — Ask "How's Project X going?" and get instant answers

## Tech Stack

- **Python 3.10+** with Slack Bolt framework
- **Slack AI capabilities** — Agent Builder, Assistant panel
- **MCP Server** — FastMCP for tool exposure
- **Real-Time Search API** — `assistant.search.context` endpoint
- **Groq (FREE)** — Llama 3.3 70B via OpenAI-compatible API (no credit card needed)
- **APScheduler** — for automated daily reports

## Quick Start

### Prerequisites
- Python 3.10+
- A Slack workspace with admin access
- OpenAI API key

### Setup

1. Clone this repo and install dependencies:
```bash
cd slackscope
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your tokens:
```bash
cp .env.example .env
```

3. Create a Slack App at https://api.slack.com/apps with these settings:
   - Enable **Socket Mode**
   - Enable **Event Subscriptions** (subscribe to `app_mention`, `message.channels`)
   - Add **Bot Token Scopes**: `app_mentions:read`, `chat:write`, `channels:read`, `channels:history`, `search:read.public`, `search:read.private`
   - Enable **Agents & AI Apps** feature
   - Create a **Slash Command**: `/slackscope`

4. Run the app:
```bash
python app.py
```

## Architecture

```
User @mentions SlackScope in Slack
    → Bolt event handler receives message
    → RTS API searches relevant channels for context
    → LLM analyzes messages (blockers, risks, sentiment)
    → Block Kit health report rendered
    → Response posted back to Slack

MCP Server runs alongside, exposing:
    → get_project_health(channel)
    → get_blockers(channel)
    → post_report(channel)
```

## Project Structure

```
slackscope/
├── app.py                  # Main entry point
├── config.py               # Environment configuration
├── requirements.txt        # Dependencies
├── .env.example            # Token template
│
├── agents/                 # AI analysis engine
│   ├── health_analyzer.py  # LLM-powered health scoring
│   └── report_generator.py # Report formatting
│
├── slack_handlers/         # Slack event/command handlers
│   ├── events.py           # @mention handling
│   ├── commands.py         # Slash command handling
│   └── actions.py          # Button/modal interactions
│
├── services/               # Core services
│   ├── rts_search.py       # Real-Time Search API wrapper
│   ├── channel_monitor.py  # Channel scanning
│   └── scheduler.py        # Daily report scheduler
│
├── mcp_server/             # Model Context Protocol server
│   ├── server.py           # FastMCP entry point
│   └── tools.py            # Tool definitions
│
└── ui/                     # UI components
    └── blocks.py           # Block Kit message builders
```

## License

MIT
