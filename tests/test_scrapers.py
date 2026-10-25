from datetime import datetime, timedelta

import scrapers
from config import SOFIA_TZ
from models import Article, db
from scrapers import NewsBgScraper, RssScraper, fetch_all, save_articles

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item><title>Първа новина</title><link>https://example.bg/1</link><pubDate>Sun, 25 Oct 2026 13:40:30 +0200</pubDate></item>
<item><title>Втора новина</title><link>https://example.bg/2</link><pubDate>Sun, 25 Oct 2026 11:30:00 +0000</pubDate></item>
<item><title>Без дата</title><link>https://example.bg/3</link></item>
<item><title></title><link>https://example.bg/4</link></item>
</channel></rss>""".encode()

NEWS_BG_HOME = """<html><body>
<div class="topic"><h2><a class="title" href="/bg/a1">Заглавие едно</a></h2><p class="time">преди 5 минути</p></div>
<div class="topic"><h2><a class="title" href="/bg/a2">Заглавие две</a></h2></div>
<div class="topic"><h2><a class="title" href="/bg/a3">Заглавие три</a></h2></div>
</body></html>""".encode()

NEWS_BG_ARTICLE = b'<html><head><meta property="article:published_time" content="2026-10-25T10:00:00+03:00"></head></html>'


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def fake_get(pages: dict):
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return FakeResponse(pages[url])

    get.calls = calls
    return get


def test_rss_scraper_parses_items_in_sofia_time(monkeypatch):
    monkeypatch.setattr(scrapers.requests, 'get', fake_get({'https://example.bg/rss': RSS}))
    articles = RssScraper('Test', 'https://example.bg/rss').fetch()

    assert [a['title'] for a in articles] == ['Първа новина', 'Втора новина', 'Без дата']
    assert articles[0]['published'].replace(tzinfo=None) == datetime(2026, 10, 25, 13, 40, 30)
    assert articles[1]['published'].replace(tzinfo=None) == datetime(2026, 10, 25, 13, 30)  # UTC -> EET
    assert datetime.now(SOFIA_TZ) - articles[2]['published'] < timedelta(minutes=1)  # no date -> now


def test_news_bg_skips_known_links_and_fetches_only_missing_times(monkeypatch):
    get = fake_get({
        'https://news.bg/': NEWS_BG_HOME,
        'https://news.bg/bg/a2': NEWS_BG_ARTICLE,
    })
    monkeypatch.setattr(scrapers.requests, 'get', get)

    articles = NewsBgScraper('News.bg', 'https://news.bg/').fetch(known_links={'https://news.bg/bg/a3'})

    assert [a['link'] for a in articles] == ['https://news.bg/bg/a1', 'https://news.bg/bg/a2']
    # a1 had a homepage time, a3 is already stored: only a2's page is fetched
    assert get.calls == ['https://news.bg/', 'https://news.bg/bg/a2']
    assert articles[1]['published'].replace(tzinfo=None) == datetime(2026, 10, 25, 9, 0)


def test_fetch_all_drops_known_and_expired_articles(monkeypatch, make_article):
    class FakeScraper:
        source = 'Fake'

        def fetch(self, known_links=frozenset()):
            return [
                make_article('Ново', 'https://x.bg/new'),
                make_article('Вече записано', 'https://x.bg/known'),
                make_article('Много старо', 'https://x.bg/old', minutes_ago=60 * 24 * 365),
            ]

    monkeypatch.setattr(scrapers, 'SCRAPERS', [FakeScraper()])
    articles = fetch_all(known_links={'https://x.bg/known'})

    assert [a['link'] for a in articles] == ['https://x.bg/new']
    assert articles[0]['category'] == 'other'


def test_save_groups_cross_source_duplicates(app_ctx, make_article):
    title = 'Радев: Убийствата вероятно ще продължат, защото олигархията губи контрол'
    save_articles(db, Article, [make_article(title, 'https://dnevnik.bg/1', source='Dnevnik')])
    added = save_articles(db, Article, [
        make_article('Румен ' + title, 'https://dir.bg/1', source='Dir.bg'),          # other source: grouped
        make_article(title + '!', 'https://dnevnik.bg/1-repost', source='Dnevnik'),   # same source: skipped
        make_article('Нещо', 'javascript:alert(1)', source='Dir.bg'),                 # bad scheme: skipped
    ])

    assert [a.link for a in added] == ['https://dir.bg/1']
    original = Article.query.filter_by(link='https://dnevnik.bg/1').one()
    assert added[0].duplicate_of == original.id
    assert original.to_dict()['also_in'] == [{'source': 'Dir.bg', 'link': 'https://dir.bg/1'}]


def test_save_groups_duplicates_within_one_batch(app_ctx, make_article):
    title = 'ЦИК: Всички секции са отворени, само в три е преминато към хартиено гласуване'
    added = save_articles(db, Article, [
        make_article(title, 'https://a.bg/1', source='24chasa'),
        make_article(title, 'https://b.bg/1', source='Sega'),
    ])

    assert added[1].original is added[0]
