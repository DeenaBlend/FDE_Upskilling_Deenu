# AI Upskill Project

**Multi-agent news aggregation system with MCP integration**

A production-ready AI agent pipeline that fetches, filters, summarizes, and writes AI/ML news newsletters.

## Features

- 🚀 **Async News Fetching** from multiple sources (HackerNews, RSS)
- 🤖 **AI-Powered Filtering** via LiteLLM (default: Claude Haiku 4.5; swap providers via env var)
- 🔧 **MCP Integration** with reusable tools
- 📝 **Multi-Agent Pipeline** (Filter → Summarize → Write)
- 💾 **SQLite Database** for article storage
- 📊 **Evaluation Framework** for quality measurement
- ✅ **60%+ Test Coverage**

## Quick Start

### Prerequisites

- Python 3.11+
- One LLM provider API key (Anthropic recommended; OpenAI, Gemini, or any other [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers) also works)

### Installation

```bash
# Clone repo
git clone https://github.com/BLEND360/AIUpskillProject.git
cd AIUpskillProject

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your provider API key
```

### Run Complete Pipeline

```bash
# Run the complete pipeline
python src/complete_pipeline.py

# Output will be in:
# - data/output/newsletter.md (final newsletter)
# - data/context/ (intermediate outputs)
# - data/news_agent.db (article database)
```

### Run Individual Components

```bash
# Fetch articles only
python -m src.main

# Filter articles with AI
python src/pipeline.py

# Evaluate filtering quality
python src/evaluation/evaluator.py
```

## Architecture

```text
┌─────────────────────────────────────────────┐
│                News Sources                 │
│  HackerNews | RSS Feeds | GitHub Trending   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ Fetch Orchestrator  │
            │    (Milestone 1)    │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │      Database       │ ← MCP Server
            │      (SQLite)       │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │     FilterAgent     │
            │    (LLM + Tools)    │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   SummarizerAgent   │
            │   (+ SearchSkill)   │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │     WriterAgent     │
            │    (Newsletter)     │
            └──────────┬──────────┘
                       │
                       ▼
               📄 Newsletter.md
```

## Project Structure

```text
AIUpskillProject/
├── src/
│   ├── agents/          # AI agents
│   │   ├── base_agent.py
│   │   ├── news_filter_agent.py
│   │   ├── summarizer_agent.py
│   │   └── writer_agent.py
│   ├── fetchers/        # News fetchers
│   ├── mcp_servers/     # MCP servers
│   │   ├── database_server.py
│   │   └── simple_client.py
│   ├── skills/          # Reusable skills
│   │   └── search_skill.py
│   ├── tools/           # LLM-callable tools (calculator, web_search)
│   ├── evaluation/      # Evaluation framework
│   └── complete_pipeline.py
├── tests/               # Test suite
├── data/
│   ├── articles/        # Fetched articles
│   ├── context/         # Agent outputs
│   ├── output/          # Final newsletter
│   └── evaluation/      # Evaluation data
└── docs/                # Documentation
```

## Key Technologies

- **Python 3.11+** — Core language
- **aiohttp** — Async HTTP requests
- **LiteLLM** — LLM provider abstraction (default: Claude Haiku 4.5)
- **MCP** — Model Context Protocol
- **SQLite** — Local database
- **pytest** — Testing framework
- **ruff** — Formatting + linting

## Milestones Completed

- ✅ Milestone 0: Setup
- ✅ Milestone 1: Async News Fetcher
- ✅ Milestone 2: SOLID Refactoring
- ✅ Milestone 3: First Agent with Tools
- ✅ Milestone 4: MCP-Powered Pipeline
- ✅ Milestone 5: Evaluation & Documentation

## Evaluation Metrics

- **Accuracy:** 85%+
- **Precision:** 90%+
- **Recall:** 80%+
- **F1 Score:** 0.850+

See: [`data/evaluation/evaluation_report.md`](data/evaluation/evaluation_report.md)

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Target: 60%+ coverage ✅
```

## Development

### Code Style

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
pylint src/
```

### Adding New Sources

1. Create fetcher in `src/fetchers/`
2. Inherit from `BaseFetcher`
3. Implement `fetch_articles()` and `get_source_name()`
4. Register in `FetchOrchestrator`

### Adding New MCP Tools

1. Add tool schema to MCP server
2. Implement tool function
3. Register in `@server.call_tool()`
4. Test with MCP client

## Architecture Details

### System Overview

Multi-agent AI system for news aggregation and newsletter generation.

### Design Principles

1. **SOLID Principles**
   - **Single Responsibility:** Each agent has one job
   - **Open/Closed:** Easy to add new sources/agents
   - **Dependency Inversion:** Agents depend on abstractions

2. **Design Patterns**
   - **Template Method:** `BaseAgent`
   - **Factory:** `FetcherFactory`
   - **Strategy:** Rate limiting
   - **Observer:** Pipeline coordination

3. **Async-First**
   - All I/O is async
   - Concurrent fetching
   - Non-blocking operations

### Component Details

#### 1. Fetchers (Milestone 1)

**Purpose:** Fetch articles from external sources

**Sources:**

- HackerNews API
- RSS feeds

**Key Features:**

- Async concurrent fetching
- Rate limiting (10 concurrent max)
- Error handling
- Markdown output

#### 2. Agents (Milestones 3-4)

**BaseAgent:**

- Template Method pattern
- Consistent lifecycle: load → process → save
- LLM integration
- Tool support

**NewsFilterAgent:**

- Filters AI/ML relevant articles
- Uses the configured LLM (via LiteLLM) for classification
- Returns relevance scores
- JSON output parsing

**SummarizerAgent:**

- Groups articles by topic
- Generates topic summaries
- Can use SearchSkill for context

**WriterAgent:**

- Writes engaging newsletter
- Professional tone
- Structured format

#### 3. MCP Integration (Milestone 4)

**Database MCP Server:**

- Provides 3 tools: `query`, `search`, `get_sources`
- SQLite backend
- Stdio transport

**SearchSkill:**

- High-level abstraction over MCP
- Combines database search
- Reusable across agents

#### 4. Pipeline Orchestration

**Flow:** Fetch → Database → Filter → Summarize → Write

**Error Handling:**

- Each stage independent
- Graceful degradation
- Continue on errors

#### 5. Evaluation (Milestone 5)

**Golden Dataset:**

- 10 hand-labeled examples
- Covers edge cases
- Balanced (5 relevant, 5 not)

**Metrics:**

- **Accuracy:** Overall correctness
- **Precision:** Relevant accuracy
- **Recall:** Find all relevant
- **F1:** Harmonic mean

### Data Flow

```text
External APIs
      ↓
Fetchers (async)
      ↓
Markdown Files + Database
      ↓
FilterAgent (LLM via LiteLLM)
      ↓
Filtered Markdown
      ↓
SummarizerAgent (LLM + SearchSkill)
      ↓
Summary Markdown
      ↓
WriterAgent (LLM)
      ↓
Newsletter Markdown
```

### Technology Choices

**Why Python?**

- Excellent async support
- Rich AI/ML ecosystem
- Easy to learn and maintain

**Why LiteLLM + Claude Haiku 4.5?**

- LiteLLM lets us swap providers via env var — no code changes
- Claude Haiku is cheap (~$1.50 for the whole curriculum at typical usage)
- Anthropic's $5 trial credit covers it without paying
- Solid function-calling and JSON output support
- Aligns with Blend's broader Claude tooling

**Why SQLite?**

- No server required
- Perfect for local development
- Easy to deploy

**Why MCP?**

- Industry standard emerging
- Tool reusability
- LLM-agnostic

**Why Markdown?**

- Human-readable
- Git-friendly
- Easy to debug
- Flexible format

### Performance

**Metrics:**

- **Fetch 30 articles:** ~2-3 seconds
- **Filter 30 articles:** ~30-45 seconds
- **Complete pipeline:** ~2-3 minutes

**Bottlenecks:**

- LLM API calls (rate limited)
- Network I/O

**Optimizations:**

- Concurrent fetching
- Rate limiting
- Caching (future)

### Security

**API Keys:**

- Stored in `.env` (not committed)
- Loaded at runtime
- Never logged

**Input Validation:**

- URL validation
- SQL injection prevention (parameterized queries)
- LLM output parsing (safe JSON)

**Rate Limiting:**

- Prevents API abuse
- Semaphore-based
- Configurable

### Future Enhancements

1. **More Sources**
   - Twitter API
   - Reddit
   - Research papers (arXiv)

2. **Better Evaluation**
   - Larger golden dataset
   - A/B testing framework
   - Human feedback loop

3. **Deployment**
   - Docker container
   - Scheduled runs (cron)
   - Web interface

4. **Advanced Features**
   - Semantic search
   - Personalization
   - Multi-language support

## Deployment Guide

Local deployment is recommended for learning — this project is designed to run locally, no cloud deployment needed!

### Requirements

- macOS, Linux, or Windows
- Python 3.11+
- 2GB RAM
- 1GB disk space

### Setup

See [Installation](#installation) above.

### Running

```bash
# Activate environment
source venv/bin/activate

# Run pipeline
python src/complete_pipeline.py
```

### Scheduling

**macOS/Linux (cron):**

```bash
# Edit crontab
crontab -e

# Add line to run daily at 9 AM
0 9 * * * cd /path/to/project && /path/to/venv/bin/python src/complete_pipeline.py
```

**Windows (Task Scheduler):**

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 9 AM
4. Action: Start a program
   - **Program:** `C:\path\to\venv\Scripts\python.exe`
   - **Arguments:** `src/complete_pipeline.py`
   - **Start in:** `C:\path\to\project`

### Docker (Optional)

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "src/complete_pipeline.py"]
```

**Build and run:**

```bash
docker build -t aiupskillproject .
docker run -v $(pwd)/data:/app/data aiupskillproject
```

### Configuration

**Environment Variables:**

- `LITELLM_MODEL` — Required (default: `claude-haiku-4-5-20251001`)
- `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` / `GEMINI_API_KEY` / etc.) — Required, must match the provider in `LITELLM_MODEL`
- `ENVIRONMENT` — `development` / `production`
- `LOG_LEVEL` — `INFO` / `DEBUG`

### Monitoring

**Check logs:**

```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log
```

**Database size:**

```bash
# Check database
sqlite3 data/news_agent.db "SELECT COUNT(*) FROM articles;"
```

### Troubleshooting

**API rate limits:**

- Reduce fetch frequency
- Increase delays between calls

**Out of disk space:**

- Clean old articles
- Reduce retention period

**LLM errors:**

- Check API key
- Verify internet connection
- Check API quotas

## License

MIT

## Acknowledgments

Built as part of AI Agent Onboarding curriculum (v3.3).
