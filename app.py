"""
Bulgarian News Aggregator — Flask application.

Serves a real-time dashboard of categorized Bulgarian news.
Articles are fetched on a schedule and pushed to clients via SSE.

Run locally with `python app.py`; in production with gunicorn via wsgi.py.
"""

import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timedelta

import schedule
from flask import Flask, Response, jsonify, render_template, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

import importance
from config import SOFIA_TZ, Config
from models import Article, db, format_published, init_db
from scrapers import SCRAPERS, fetch_all, save_articles

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
app.jinja_env.filters['published'] = format_published

# SSE broadcast channel
sse_clients: list[queue.Queue] = []
sse_lock = threading.Lock()

# One fetch at a time — the scheduler and /api/refresh must not write concurrently
fetch_lock = threading.Lock()
last_fetch_at: float | None = None       # monotonic, for the refresh cooldown
last_fetch_time: datetime | None = None  # naive Sofia time, shown in the footer
_jobs_started = False

CATEGORIES = ['politics', 'sports', 'economy', 'tech', 'crime', 'health', 'culture', 'other']
CATEGORY_LABELS = {
    'politics': 'Политика',
    'sports': 'Спорт',
    'economy': 'Икономика',
    'tech': 'Технологии',
    'crime': 'Криминални',
    'health': 'Здраве',
    'culture': 'Култура',
    'other': 'Други',
}
SOURCES = [scraper.source for scraper in SCRAPERS]
COLUMN_SIZE = 15  # articles per dashboard section; "още" loads the next batch

WEEKDAYS = ['понеделник', 'вторник', 'сряда', 'четвъртък', 'петък', 'събота', 'неделя']
MONTHS = ['януари', 'февруари', 'март', 'април', 'май', 'юни',
          'юли', 'август', 'септември', 'октомври', 'ноември', 'декември']

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def broadcast_sse(data: dict):
    """Send an SSE message to all connected clients."""
    msg = json.dumps(data, ensure_ascii=False)
    with sse_lock:
        dead = []
        for q in sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            sse_clients.remove(q)


def last_update_label() -> str:
    return format_published(last_fetch_time) if last_fetch_time else '--:--'


def stories():
    """Primary articles only — cross-source duplicates are shown under them as "също в"."""
    return (Article.query
            .filter(Article.duplicate_of.is_(None))
            .options(selectinload(Article.duplicates))
            .order_by(Article.published.desc(), Article.id.desc()))


def count_by(column, primaries_only: bool = True) -> dict:
    q = db.session.query(column, func.count(Article.id))
    if primaries_only:
        q = q.filter(Article.duplicate_of.is_(None))
    return dict(q.group_by(column).all())


def hot_words() -> list[dict]:
    """Words several outlets are using right now (see importance.py); duplicates count."""
    since = (datetime.now(SOFIA_TZ) - timedelta(hours=importance.WINDOW_HOURS)).replace(tzinfo=None)
    rows = db.session.query(Article.title, Article.source).filter(Article.published >= since).all()
    return importance.hot_words(rows)


def get_stats() -> dict:
    by_category = count_by(Article.category)
    by_source = count_by(Article.source, primaries_only=False)
    return {
        'categories': {cat: by_category.get(cat, 0) for cat in CATEGORIES},
        'sources': {source: by_source.get(source, 0) for source in SOURCES},
        'total': sum(by_category.values()),
        'last_update': last_update_label(),
        'hot_words': hot_words(),
    }


def purge_old_articles():
    """Delete articles past the retention window, plus duplicates grouped under them."""
    cutoff = (datetime.now(SOFIA_TZ) - timedelta(days=Config.RETENTION_DAYS)).replace(tzinfo=None)
    old_ids = select(Article.id).where(Article.published < cutoff)
    deleted = Article.query.filter(
        or_(Article.published < cutoff, Article.duplicate_of.in_(old_ids))
    ).delete(synchronize_session=False)
    db.session.commit()
    if deleted:
        logger.info("Purged %d articles older than %d days", deleted, Config.RETENTION_DAYS)


def run_fetch(blocking: bool = True) -> int | None:
    """Fetch, save, broadcast. Returns new-article count, or None if a fetch is already running."""
    global last_fetch_at, last_fetch_time
    if not fetch_lock.acquire(blocking=blocking):
        return None
    try:
        known_links = {link for (link,) in db.session.query(Article.link)}
        added = save_articles(db, Article, fetch_all(known_links))
        purge_old_articles()
        last_fetch_at = time.monotonic()
        last_fetch_time = datetime.now(SOFIA_TZ).replace(tzinfo=None)
        # Push the rows themselves so open pages update in place instead of reloading
        payload = {
            'type': 'fetch',
            'last_update': last_update_label(),
            'articles': [a.to_dict() for a in added],
            'hot_words': hot_words(),
        }
    finally:
        fetch_lock.release()
    broadcast_sse(payload)
    return len(added)


@app.context_processor
def inject_dateline():
    now = datetime.now(SOFIA_TZ)
    return {
        'last_update': last_update_label(),
        'current_year': now.year,
        'today_label': f"{WEEKDAYS[now.weekday()]}, {now.day} {MONTHS[now.month - 1]} {now.year} г.",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    categorized = {
        cat: stories().filter_by(category=cat).limit(COLUMN_SIZE).all()
        for cat in CATEGORIES
    }
    stats = get_stats()

    return render_template(
        'index.html',
        categorized=categorized,
        category_labels=CATEGORY_LABELS,
        categories=CATEGORIES,
        stats=stats['categories'],
        source_stats=stats['sources'],
        total=stats['total'],
        column_size=COLUMN_SIZE,
        importance={'hot': stats['hot_words'], 'urgent': importance.URGENT_WORDS},
    )


@app.route('/api/search')
def search_articles():
    # Split keywords by comma and strip whitespace
    keywords = [k.strip() for k in request.args.get('q', '').split(',') if k.strip()]
    if not keywords:
        return jsonify([])

    # Build OR filter for all keywords
    filters = [Article.title.ilike(f'%{k}%') for k in keywords]
    articles = stories().filter(or_(*filters)).limit(100).all()

    return jsonify([a.to_dict() for a in articles])


@app.route('/api/news')
def api_news():
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(max(1, request.args.get('per_page', 60, type=int)), 100)
    # offset wins over page: the dashboard's "load more" passes how many items it already shows
    offset = request.args.get('offset', type=int)
    offset = max(0, offset) if offset is not None else (page - 1) * per_page
    category = request.args.get('category')

    q = stories()
    if category in CATEGORIES:
        q = q.filter_by(category=category)

    total = q.count()
    articles = q.offset(offset).limit(per_page).all()

    return jsonify({
        'articles': [a.to_dict() for a in articles],
        'total': total,
        'pages': max(1, (total + per_page - 1) // per_page),
        'current_page': page,
    })


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


@app.route('/api/refresh', methods=['POST'])
def refresh():
    """Manually trigger a news fetch. Rate-limited, since each call hits every source."""
    if last_fetch_at is not None:
        wait = Config.REFRESH_COOLDOWN_SECONDS - (time.monotonic() - last_fetch_at)
        if wait > 0:
            return (jsonify({'message': 'Fetched recently', 'added': 0}), 429,
                    {'Retry-After': str(int(wait) + 1)})
    try:
        added = run_fetch(blocking=False)
    except Exception as e:
        logger.error("Manual refresh failed: %s", e)
        return jsonify({'error': str(e)}), 500
    if added is None:
        return jsonify({'message': 'Fetch already running', 'added': 0}), 429
    return jsonify({'message': f'Added {added} new articles', 'added': added})


@app.route('/events')
def sse_events():
    """SSE endpoint — clients connect here for real-time updates."""
    client_queue = queue.Queue(maxsize=50)
    with sse_lock:
        sse_clients.append(client_queue)

    def stream():
        try:
            yield ": connected\n\n"  # flush headers now so the browser's onopen fires right away
            while True:
                try:
                    msg = client_queue.get(timeout=25)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except GeneratorExit:
            pass
        finally:
            with sse_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

def scheduled_fetch():
    """Background job: fetch, save, broadcast."""
    with app.app_context():
        logger.info("Scheduled fetch starting...")
        try:
            added = run_fetch()
            logger.info("Scheduled fetch done: %d new articles", added)
        except Exception as e:
            logger.error("Scheduled fetch failed: %s", e)


def run_scheduler():
    scheduled_fetch()  # initial fetch, without holding up server start
    schedule.every(Config.FETCH_INTERVAL_MINUTES).minutes.do(scheduled_fetch)
    while True:
        schedule.run_pending()
        time.sleep(1)


def start_background_jobs():
    """Prepare the DB and start the fetch scheduler. Call once per process:
    from __main__ below, or from wsgi.py under gunicorn (single worker, no --preload)."""
    global _jobs_started
    if _jobs_started:
        return
    _jobs_started = True
    with app.app_context():
        init_db()
        logger.info("Database ready")
    threading.Thread(target=run_scheduler, daemon=True).start()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    start_background_jobs()
    # Debug mode (Werkzeug debugger = remote code execution) only via FLASK_DEBUG=1
    app.run(port=int(os.environ.get('PORT', 5000)), use_reloader=False)
