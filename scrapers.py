"""
News scrapers for Bulgarian news sources.

Each scraper fetches articles from a specific source, returning a list of dicts:
    {'title': str, 'link': str, 'published': datetime, 'source': str}

The aggregator orchestrates all scrapers, classifies articles, and persists them.
"""

import difflib
import logging
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

from classifier import classify
from config import SOFIA_TZ, Config

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all news scrapers."""

    def __init__(self, source: str, url: str, limit: int = Config.ARTICLES_PER_SOURCE):
        self.source = source
        self.url = url
        self.limit = limit

    def _get_soup(self) -> BeautifulSoup | None:
        try:
            resp = requests.get(
                self.url,
                timeout=Config.REQUEST_TIMEOUT,
                headers={'User-Agent': Config.USER_AGENT},
            )
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'html.parser')
        except requests.RequestException as e:
            logger.error("Failed to fetch %s: %s", self.url, e)
            return None

    def _now(self) -> datetime:
        return datetime.now(SOFIA_TZ)

    @abstractmethod
    def fetch(self, known_links: set[str] = frozenset()) -> list[dict]:
        """Return list of article dicts. known_links are already stored and may be skipped."""

    def _make_absolute(self, href: str) -> str:
        if href.startswith('http'):
            return href
        base = self.url.rstrip('/')
        return f"{base}{href}" if href.startswith('/') else f"{base}/{href}"


class RssScraper(BaseScraper):
    """Generic RSS-based scraper. Works for any site with a standard RSS feed."""

    def fetch(self, known_links: set[str] = frozenset()) -> list[dict]:
        try:
            resp = requests.get(
                self.url,
                timeout=Config.REQUEST_TIMEOUT,
                headers={'User-Agent': Config.USER_AGENT},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'xml')
        except requests.RequestException as e:
            logger.error("Failed to fetch RSS %s: %s", self.url, e)
            return []

        articles = []
        for item in soup.find_all('item'):
            if len(articles) >= self.limit:
                break

            title_el = item.find('title')
            link_el = item.find('link')
            pubdate_el = item.find('pubDate')

            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            link = link_el.get_text(strip=True)
            if not title or not link:
                continue

            published = self._now()
            if pubdate_el and pubdate_el.text.strip():
                try:
                    published = parsedate_to_datetime(pubdate_el.text.strip()).astimezone(SOFIA_TZ)
                except (ValueError, TypeError):
                    pass

            articles.append({
                'title': title, 'link': link,
                'published': published, 'source': self.source,
            })

        return articles


class NewsBgScraper(BaseScraper):
    """Scraper for news.bg — fetches article:published_time from article pages."""

    _RELATIVE_RE = re.compile(r'(\d+)\s+(минут|час|ден)')

    def fetch(self, known_links: set[str] = frozenset()) -> list[dict]:
        soup = self._get_soup()
        if not soup:
            return []

        # Collect raw articles from homepage
        raw = []
        seen_links = set()
        for topic in soup.select('div.topic'):
            if len(raw) >= self.limit:
                break

            title_el = topic.select_one('h2 a.title')
            if not title_el or not title_el.get('href'):
                continue

            title = title_el.get_text(strip=True)
            link = title_el['href'].strip()
            if not title or link in seen_links:
                continue
            seen_links.add(link)
            if not link.startswith('http'):
                link = self._make_absolute(link)
            if link in known_links:
                continue  # already stored — don't re-fetch its article page

            # Use homepage relative time if available
            time_el = topic.select_one('p.time')
            homepage_time = self._parse_relative(time_el.get_text(strip=True)) if time_el else None

            raw.append({'title': title, 'link': link, 'homepage_time': homepage_time})

        # For articles missing time, fetch article pages in parallel
        needs_fetch = [a for a in raw if a['homepage_time'] is None]
        fetched_times = {}
        if needs_fetch:
            logger.info("News.bg: fetching %d article pages for publish times", len(needs_fetch))
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(self._fetch_article_time, a['link']): a['link'] for a in needs_fetch}
                for future in as_completed(futures):
                    link = futures[future]
                    try:
                        fetched_times[link] = future.result()
                    except Exception:
                        fetched_times[link] = None

        articles = []
        for a in raw:
            published = a['homepage_time'] or fetched_times.get(a['link']) or self._now()
            articles.append({
                'title': a['title'], 'link': a['link'],
                'published': published, 'source': self.source,
            })

        return articles

    def _fetch_article_time(self, url: str) -> datetime | None:
        """Fetch an article page and extract article:published_time meta tag."""
        try:
            resp = requests.get(url, timeout=Config.REQUEST_TIMEOUT,
                                headers={'User-Agent': Config.USER_AGENT})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            meta = soup.find('meta', attrs={'property': 'article:published_time'})
            if meta and meta.get('content'):
                return datetime.fromisoformat(meta['content']).astimezone(SOFIA_TZ)
        except Exception as e:
            logger.debug("news.bg article time fetch failed for %s: %s", url, e)
        return None

    def _parse_relative(self, text: str) -> datetime | None:
        """Parse 'преди N минути/часа/дни'."""
        m = self._RELATIVE_RE.search(text)
        if m:
            value = int(m.group(1))
            unit = m.group(2)
            if 'минут' in unit:
                delta = timedelta(minutes=value)
            elif 'час' in unit:
                delta = timedelta(hours=value)
            elif 'ден' in unit:
                delta = timedelta(days=value)
            else:
                return None
            return self._now() - delta
        return None


# Registry of all scrapers
SCRAPERS = [
    RssScraper('24chasa', 'https://www.24chasa.bg/rss'),
    RssScraper('Dnevnik', 'https://www.dnevnik.bg/rss/'),
    RssScraper('Fakti', 'https://fakti.bg/feed'),
    RssScraper('Mediapool', 'https://www.mediapool.bg/rss'),
    RssScraper('Dir.bg', 'https://dnes.dir.bg/support/cat_rss.php'),
    NewsBgScraper('News.bg', 'https://news.bg/'),
    RssScraper('Sega', 'https://segabg.com/rss'),
]


def fetch_all(known_links: set[str] = frozenset()) -> list[dict]:
    """
    Fetch articles from all sources in parallel, classify them, return list of dicts.
    Links in known_links (already stored) and articles past retention are dropped.
    """
    all_articles = []
    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as pool:
        futures = [pool.submit(scraper.fetch, known_links) for scraper in SCRAPERS]
        # Collect in registry order so the same source wins duplicate grouping every run
        for scraper, future in zip(SCRAPERS, futures):
            try:
                articles = future.result()
                logger.info("Fetched %d articles from %s", len(articles), scraper.source)
                all_articles.extend(articles)
            except Exception as e:
                logger.error("Scraper %s failed: %s", scraper.source, e)

    cutoff = datetime.now(SOFIA_TZ) - timedelta(days=Config.RETENTION_DAYS)
    all_articles = [
        a for a in all_articles
        if a['link'] not in known_links and a['published'] >= cutoff
    ]

    # Classify each article
    for article in all_articles:
        article['category'] = classify(article['title'])

    return all_articles


def save_articles(db, Article, articles: list[dict]) -> list:
    """
    Persist new articles. A story another source already covered in the last 48h
    (fuzzy title match) is stored as a duplicate of it and shown under it as "също в";
    a near-identical re-post from the same source is skipped.
    Returns the newly inserted Article rows.
    """
    # The database stores naive Sofia-local datetimes
    recent_cutoff = (datetime.now(SOFIA_TZ) - timedelta(days=2)).replace(tzinfo=None)
    candidates = Article.query.filter(
        Article.published >= recent_cutoff, Article.duplicate_of.is_(None)
    ).all()

    added = []
    for a in articles:
        # Links end up in href attributes — never store javascript: or other schemes
        if not a['link'].startswith(('http://', 'https://')):
            continue

        # Check exact link match
        if db.session.query(Article.id).filter_by(link=a['link']).first():
            continue

        # Check fuzzy title match (difflib ratio: 0..1)
        original = next(
            (c for c in candidates
             if difflib.SequenceMatcher(None, a['title'], c.title).ratio() > 0.85),
            None,
        )
        if original is not None and original.source == a['source']:
            logger.info("Skipped same-source duplicate: '%s' matches '%s'", a['title'], original.title)
            continue

        # Convert localized datetime to naive for DB storage
        naive_pub = a['published']
        if naive_pub.tzinfo is not None:
            naive_pub = naive_pub.replace(tzinfo=None)

        article = Article(
            title=a['title'],
            link=a['link'],
            published=naive_pub,
            source=a['source'],
            category=a['category'],
            original=original,
        )
        db.session.add(article)
        added.append(article)
        if original is None:
            # Later articles in this batch can be grouped under it too
            candidates.append(article)
        else:
            logger.info("Grouped '%s' (%s) under '%s' (%s)", a['title'], a['source'], original.title, original.source)

    db.session.commit()
    logger.info("Inserted %d new articles (%d grouped as duplicates)",
                len(added), sum(1 for a in added if a.original is not None))
    return added
