"""Smoke test against the real sites — catches a feed URL or HTML layout change
(the kind of break that left Fakti at 3 articles). Run with: LIVE=1 pytest -m live"""

import os

import pytest

from scrapers import SCRAPERS

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get('LIVE') != '1', reason='set LIVE=1 to hit the real sites'),
]


@pytest.mark.parametrize('scraper', SCRAPERS, ids=lambda s: s.source)
def test_source_still_returns_articles(scraper):
    articles = scraper.fetch()
    assert len(articles) >= 5, f"{scraper.source} returned {len(articles)} articles — feed URL or layout changed?"
    assert all(a['title'] and a['link'].startswith('http') for a in articles)
