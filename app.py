"""
Bulgarian News Aggregator — Flask application.

Serves a real-time dashboard of categorized Bulgarian news.
Articles are fetched on a schedule and pushed to clients via SSE.
"""

import json
import logging
import queue
import threading
import time

import schedule
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

from config import Config
from models import Article, db
from scrapers import fetch_all, save_articles

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
CORS(app)

# SSE broadcast channel
sse_clients: list[queue.Queue] = []
sse_lock = threading.Lock()

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

# ---------------------------------------------------------------------------
# SSE helpers
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 30

    # Query each category from DB directly (not loading everything into Python)
    categorized = {}
    for cat in CATEGORIES:
        q = Article.query.filter_by(category=cat).order_by(Article.published.desc())
        categorized[cat] = q.limit(per_page).offset((page - 1) * per_page).all()

    total = Article.query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Stats
    stats = {}
    for cat in CATEGORIES:
        stats[cat] = Article.query.filter_by(category=cat).count()

    source_stats = {}
    for source_name in ['24chasa', 'Dnevnik', 'Fakti', 'Mediapool', 'Dir.bg', 'News.bg', 'Sega']:
        source_stats[source_name] = Article.query.filter_by(source=source_name).count()

    return render_template(
        'index.html',
        categorized=categorized,
        category_labels=CATEGORY_LABELS,
        categories=CATEGORIES,
        stats=stats,
        source_stats=source_stats,
        total=total,
        page=page,
        total_pages=total_pages,
    )


@app.route('/api/search')
def search_articles():
    query_str = request.args.get('q', '').strip()
    if not query_str:
        return jsonify([])
    
    # Split keywords by comma and strip whitespace
    keywords = [k.strip() for k in query_str.split(',') if k.strip()]
    if not keywords:
        return jsonify([])

    from sqlalchemy import or_
    
    # Build OR filter for all keywords
    filters = [Article.title.ilike(f'%{k}%') for k in keywords]
    articles = Article.query.filter(or_(*filters)).order_by(Article.published.desc()).limit(100).all()
    
    return jsonify([{
        'id': a.id,
        'title': a.title,
        'link': a.link,
        'source': a.source,
        'category': a.category,
        'published': a.published.strftime('%H:%M')
    } for a in articles])


@app.route('/api/news')
def api_news():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 60, type=int)
    category = request.args.get('category')

    q = Article.query.order_by(Article.published.desc())
    if category and category in CATEGORIES:
        q = q.filter_by(category=category)

    total = q.count()
    articles = q.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'articles': [a.to_dict() for a in articles],
        'total': total,
        'pages': max(1, (total + per_page - 1) // per_page),
        'current_page': page,
    })


@app.route('/api/stats')
def api_stats():
    stats = {cat: Article.query.filter_by(category=cat).count() for cat in CATEGORIES}
    sources = {}
    for s in ['24chasa', 'Dnevnik', 'Fakti', 'Mediapool', 'Dir.bg', 'News.bg', 'Sega']:
        sources[s] = Article.query.filter_by(source=s).count()
    return jsonify({'categories': stats, 'sources': sources, 'total': Article.query.count()})


@app.route('/api/refresh', methods=['POST'])
def refresh():
    """Manually trigger a news fetch."""
    try:
        articles = fetch_all()
        added = save_articles(db, Article, articles)
        if added > 0:
            broadcast_sse({'type': 'update', 'count': added})
        return jsonify({'message': f'Added {added} new articles', 'added': added})
    except Exception as e:
        logger.error("Manual refresh failed: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/events')
def sse_events():
    """SSE endpoint — clients connect here for real-time updates."""
    client_queue = queue.Queue(maxsize=50)
    with sse_lock:
        sse_clients.append(client_queue)

    def stream():
        try:
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
            articles = fetch_all()
            added = save_articles(db, Article, articles)
            if added > 0:
                broadcast_sse({'type': 'update', 'count': added})
            logger.info("Scheduled fetch done: %d new articles", added)
        except Exception as e:
            logger.error("Scheduled fetch failed: %s", e)


def run_scheduler():
    schedule.every(Config.FETCH_INTERVAL_MINUTES).minutes.do(scheduled_fetch)
    while True:
        schedule.run_pending()
        time.sleep(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database ready")

        # Initial fetch on startup
        articles = fetch_all()
        save_articles(db, Article, articles)

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    app.run(debug=True, use_reloader=False)
