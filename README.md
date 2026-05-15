# WebScraper API

## Endpoints

### Scrape a URL (async)
```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "format": "json"}'
# Returns: {"job_id": "abc123", "url": "...", "status": "pending"}

# Check result
curl http://localhost:8000/scrape/abc123
```

### Scrape a URL (sync - direct response)
```bash
curl -X POST http://localhost:8000/scrape/sync \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "mode": "headless", "format": "markdown"}'
```

### Scrape with extraction filter
```bash
curl -X POST http://localhost:8000/scrape/sync \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "extract": ["emails", "phones", "social_links", "tables"]}'
```

### Schedule a recurring scrape
```bash
# Every 30 minutes
curl -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "schedule": "30m"}'

# Cron: every day at 9 AM
curl -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "schedule": "0 9 * * *"}'

# List schedules
curl http://localhost:8000/schedule

# Get results for a schedule
curl http://localhost:8000/schedule/{job_id}/results
```

### Other
```bash
curl http://localhost:8000/          # API info
curl http://localhost:8000/health    # Health check
curl http://localhost:8000/jobs      # List all scrape jobs
```

## Setup

```bash
cd /home/fatboy/Documents/server/production/webscraper

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install deps
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy env
cp .env.example .env

# Run dev
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# API docs: http://localhost:8000/docs
```

## Export Formats

| Format | Extension | Use case |
|--------|-----------|----------|
| json   | .json     | API integration, programmatic use |
| csv    | .csv      | Spreadsheet analysis |
| markdown | .md      | Human-readable reports |
| html   | .html     | Visual reports, browser viewing |

## Modes

| Mode     | Speed | JS Support | Use case |
|----------|-------|------------|----------|
| static   | Fast  | No         | Static HTML pages, blogs, docs |
| headless | Slow  | Full       | React/Vue/SPAs, infinite scroll |
| auto     | Smart | Adaptive   | Tries static first, falls back to headless |
