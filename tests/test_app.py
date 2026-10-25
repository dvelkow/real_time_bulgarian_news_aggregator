from datetime import datetime, timedelta

from sqlalchemy import inspect, text

import app as app_module
from config import SOFIA_TZ
from models import Article, db, format_published, init_db
from scrapers import save_articles

# Distinct enough that fuzzy duplicate detection leaves them alone
TITLES = ['Пожар в Пловдив', 'Наводнение във Варна', 'Нов мост над Дунав', 'Концерт в Русе', 'Протест в Бургас']


def test_search_is_case_insensitive_for_cyrillic(client, make_article):
    save_articles(db, Article, [make_article('Борисов: Непоискана подкрепа на никого не даваме', 'https://x.bg/1')])

    for q in ['борисов', 'БОРИСОВ', 'Борисов', 'нищо, борисов']:
        assert len(client.get('/api/search', query_string={'q': q}).json) == 1, q
    assert client.get('/api/search', query_string={'q': 'радев'}).json == []


def test_search_lists_duplicates_under_their_original(client, make_article):
    title = 'Илияна Йотова: Вярвам, че в България ще има подем'
    save_articles(db, Article, [make_article(title, 'https://a.bg/1', source='Fakti')])
    save_articles(db, Article, [make_article(title, 'https://b.bg/1', source='Sega')])

    results = client.get('/api/search', query_string={'q': 'йотова'}).json
    assert [r['link'] for r in results] == ['https://a.bg/1']
    assert results[0]['also_in'] == [{'source': 'Sega', 'link': 'https://b.bg/1'}]


def test_api_news_clamps_and_supports_offset(client, make_article):
    save_articles(db, Article, [
        make_article(title, f'https://x.bg/{i}', minutes_ago=i) for i, title in enumerate(TITLES)
    ])

    resp = client.get('/api/news?per_page=100000&page=0').json
    assert resp['current_page'] == 1 and len(resp['articles']) == 5

    resp = client.get('/api/news?offset=3&per_page=30').json
    assert [a['link'] for a in resp['articles']] == ['https://x.bg/3', 'https://x.bg/4']


def test_refresh_is_rate_limited(client, monkeypatch, make_article):
    monkeypatch.setattr(app_module, 'fetch_all', lambda known_links: [make_article('Нова', 'https://x.bg/n')])

    first = client.post('/api/refresh')
    second = client.post('/api/refresh')

    assert first.status_code == 200 and first.json['added'] == 1
    assert second.status_code == 429 and 'Retry-After' in second.headers


def test_refresh_while_fetch_running(client):
    with app_module.fetch_lock:
        resp = client.post('/api/refresh')
    assert resp.status_code == 429
    assert resp.json['message'] == 'Fetch already running'


def test_no_cors_headers(client):
    resp = client.get('/api/stats', headers={'Origin': 'https://evil.example'})
    assert 'Access-Control-Allow-Origin' not in resp.headers


def test_stats_count_stories_and_sources(client, make_article):
    title = 'ЦИК: Всички секции са отворени, само в три е преминато към хартиено гласуване'
    save_articles(db, Article, [
        make_article(title, 'https://a.bg/1', source='24chasa', category='politics'),
        make_article(title, 'https://b.bg/1', source='Sega', category='politics'),
        make_article('Левски би', 'https://c.bg/1', source='Sega', category='sports'),
    ])

    stats = client.get('/api/stats').json
    assert stats['hot_words'] == []  # 'ЦИК' is used by only 2 outlets here
    assert stats['total'] == 2  # the Sega duplicate is not a separate story
    assert stats['categories']['politics'] == 1 and stats['categories']['sports'] == 1
    assert stats['sources']['Sega'] == 2 and stats['sources']['24chasa'] == 1


def test_index_renders_every_column_with_load_more(client, make_article, monkeypatch):
    monkeypatch.setattr(app_module, 'COLUMN_SIZE', 2)
    save_articles(db, Article, [
        make_article(title, f'https://x.bg/{i}', category='crime', minutes_ago=i) for i, title in enumerate(TITLES[:3])
    ])

    html = client.get('/').get_data(as_text=True)
    assert html.count('<section class="section"') == len(app_module.CATEGORIES)
    assert 'data-category="crime" data-page-size="2"' in html
    assert 'няма новини' in html  # empty categories still get a section
    assert 'logo' not in html
    assert '<script id="importance-data" type="application/json">' in html
    assert 'извънредно' in html  # urgent words reach the front end


def test_run_fetch_purges_expired_articles(app_ctx, monkeypatch):
    old = datetime.now(SOFIA_TZ).replace(tzinfo=None) - timedelta(days=app_module.Config.RETENTION_DAYS + 1)
    original = Article(title='Стара', link='https://x.bg/old', published=old, source='Sega', category='other')
    db.session.add(original)
    db.session.flush()
    db.session.add(Article(title='Стара също', link='https://y.bg/old', published=datetime.now(SOFIA_TZ).replace(tzinfo=None),
                           source='Fakti', category='other', duplicate_of=original.id))
    db.session.commit()
    monkeypatch.setattr(app_module, 'fetch_all', lambda known_links: [])

    app_module.run_fetch()

    assert Article.query.count() == 0


def test_init_db_migrates_old_schema(app_ctx):
    db.drop_all()
    with db.engine.begin() as conn:
        conn.execute(text(
            'CREATE TABLE articles (id INTEGER PRIMARY KEY, title VARCHAR(500) NOT NULL, link VARCHAR(500) NOT NULL UNIQUE, '
            'published DATETIME NOT NULL, source VARCHAR(50) NOT NULL, category VARCHAR(30) NOT NULL)'
        ))
        conn.execute(text("INSERT INTO articles VALUES (1, 'Т', 'https://x.bg/1', '2026-10-25 10:00:00', 'Sega', 'other')"))

    init_db()

    assert 'duplicate_of' in {c['name'] for c in inspect(db.engine).get_columns('articles')}
    assert Article.query.one().duplicate_of is None


def test_format_published():
    now = datetime.now(SOFIA_TZ).replace(tzinfo=None, second=0, microsecond=0)
    assert format_published(now) == now.strftime('%H:%M')
    assert format_published(now - timedelta(days=1)) == (now - timedelta(days=1)).strftime('вчера %H:%M')
    assert format_published(datetime(2026, 1, 5, 9, 7)) == '05.01 09:07'
