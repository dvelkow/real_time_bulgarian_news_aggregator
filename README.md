# Bulgarian News Aggregator

![Showcase](showcase.png)

A real-time news aggregator that collects, classifies, and displays the latest news from 7 major Bulgarian news sources — all in one dashboard.

## What It Does

- **Scrapes 7 sources** — 24chasa, Dnevnik, Fakti, Mediapool, Dir.bg, News.bg, and Sega
- **Auto-classifies** articles into 8 categories (Politics, Sports, Economy, Tech, Crime, Health, Culture, Other) using weighted keyword matching
- **Real-time updates** via Server-Sent Events (SSE) — new articles appear without page refresh
- **Live search** — type any word and instantly filter across all articles
- **Duplicate detection** — fuzzy title matching (85% similarity threshold) prevents the same story from appearing twice across sources
- **Draggable columns** — reorder category sections by dragging
- **Custom sections** — create your own keyword-filtered news columns saved in localStorage

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌───────────┐
│  7 Sources  │────>│   Scrapers   │────>│ Classifier│────>│  SQLite   │
│  (RSS/HTML) │     │  (parallel)  │     │ (keyword) │     │    DB     │
└─────────────┘     └──────────────┘     └──────────┘     └─────┬─────┘
                                                                │
                    ┌──────────────┐     ┌──────────┐           │
                    │  SSE Clients │<────│  Flask   │<──────────┘
                    │  (browsers)  │     │  Server  │
                    └──────────────┘     └──────────┘
```

**Scraping strategy:**
- **RSS feeds** (24chasa, Dnevnik, Mediapool, Sega) — reliable timestamps, clean data, no HTML parsing
- **HTML scraping** (Fakti, Dir.bg) — BeautifulSoup with timezone-aware date parsing
- **HTML + article page fetch** (News.bg) — homepage scrape + parallel article page requests for accurate publish times

All timestamps are normalized to `Europe/Sofia` timezone.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, SQLAlchemy, SQLite |
| Scraping | Requests, BeautifulSoup, lxml (RSS) |
| Real-time | Server-Sent Events (SSE) |
| Frontend | Jinja2 templates, vanilla JS, CSS |
| Scheduling | `schedule` library (background thread) |

## Project Structure

```
├── app.py              # Flask app, routes, SSE, scheduler
├── scrapers.py         # All 7 source scrapers (RSS + HTML)
├── classifier.py       # Keyword-based article categorization
├── models.py           # SQLAlchemy Article model
├── config.py           # App configuration
├── requirements.txt
├── templates/
│   ├── base.html       # Layout, header, search, SSE client JS
│   └── index.html      # Dashboard grid, category columns
└── static/css/
    └── styles.css
```

## Setup

```bash
git clone https://github.com/dvelkow/real_time_bulgarian_news_aggregator.git
cd real_time_bulgarian_news_aggregator

pip install -r requirements.txt

python app.py
```

The app starts at `http://127.0.0.1:5000`. On first launch it fetches all sources, creates the SQLite database, and begins the 10-minute auto-refresh cycle.

## How the Classifier Works

Each article title is scored against weighted keyword lists for 8 categories. Bulgarian-language keywords are matched case-insensitively, with multi-word phrases receiving higher weights (e.g., "Конституционен съд" = 3 points for Politics). The highest-scoring category wins; if no keywords match, the article is filed under "Other".

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `FETCH_INTERVAL_MINUTES` | 10 | Auto-refresh interval |
| `ARTICLES_PER_SOURCE` | 60 | Max articles per scraper |
| `REQUEST_TIMEOUT` | 15 | HTTP timeout in seconds |
