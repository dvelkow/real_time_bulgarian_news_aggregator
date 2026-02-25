"""
News scrapers for Bulgarian news sources.

Each scraper fetches articles from a specific source, returning a list of dicts:
    {'title': str, 'link': str, 'published': datetime, 'source': str}

The aggregator orchestrates all scrapers, classifies articles, and persists them.
"""

import logging
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import difflib

import pytz
import requests
from bs4 import BeautifulSoup

from classifier import classify
from config import Config

logger = logging.getLogger(__name__)
SOFIA_TZ = pytz.timezone('Europe/Sofia')


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

    def _localize(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return SOFIA_TZ.localize(dt)
        return dt.astimezone(SOFIA_TZ)

    def _now(self) -> datetime:
        return datetime.now(SOFIA_TZ)

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Return list of article dicts."""

    def _make_absolute(self, href: str) -> str:
        if href.startswith('http'):
            return href
        base = self.url.rstrip('/')
        return f"{base}{href}" if href.startswith('/') else f"{base}/{href}"


class RssScraper(BaseScraper):
    """Generic RSS-based scraper. Works for any site with a standard RSS feed."""

    def fetch(self) -> list[dict]:
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


class FaktiScraper(BaseScraper):
    """Scraper for fakti.bg."""

    def fetch(self) -> list[dict]:
        soup = self._get_soup()
        if not soup:
            return []

        articles = []
        for item in soup.find_all('article', class_='panel selected-ln'):
            if len(articles) >= self.limit:
                break
            title_tag = item.find('span', class_='article-title')
            if not title_tag:
                continue
            title = title_tag.text.strip()
            a_tag = item.find('a')
            if not a_tag or not a_tag.get('href'):
                continue
            link = self._make_absolute(a_tag['href'])
            date_el = item.find('div', class_='ndt')
            published = self._parse_date(date_el.text.strip()) if date_el else self._now()
            articles.append({
                'title': title, 'link': link,
                'published': published, 'source': self.source,
            })

        return articles

    def _parse_date(self, date_str: str) -> datetime:
        now = self._now()
        try:
            if 'вчера' in date_str:
                base = now - timedelta(days=1)
            elif 'днес' in date_str:
                base = now
            else:
                # Try absolute date format: DD.MM.YYYY
                m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
                if m:
                    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    # Check if there's a time component too
                    tm = re.search(r'(\d{1,2}):(\d{2})', date_str)
                    if tm:
                        return self._localize(datetime(year, month, day, int(tm.group(1)), int(tm.group(2))))
                    return self._localize(datetime(year, month, day))
                return now
            time_str = date_str.split('в')[-1].strip().replace('ч.', '').strip()
            t = datetime.strptime(time_str, '%H:%M')
            return self._localize(
                now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                - (timedelta(days=1) if 'вчера' in date_str else timedelta())
            )
        except (ValueError, TypeError) as e:
            logger.warning("Fakti date parse error '%s': %s", date_str, e)
            return now


class MediapoolScraper(RssScraper):
    """Scraper for mediapool.bg via RSS."""
    pass


class DirBgScraper(BaseScraper):
    """Scraper for dir.bg — timestamp format 'HH:MM | DD.MM.YY'."""

    def fetch(self) -> list[dict]:
        soup = self._get_soup()
        if not soup:
            return []

        articles = []
        seen_links = set()

        # Both text-news and img-news items share the same inner structure
        for item in soup.select('div.text-news.list-article, div.img-news'):
            if len(articles) >= self.limit:
                break

            title_el = item.select_one('h2.title a') or item.select_one('h3.title a')
            if not title_el or not title_el.get('href'):
                continue

            title = title_el.get_text(strip=True)
            link = title_el['href'].strip()
            if not title or link in seen_links:
                continue
            seen_links.add(link)

            if not link.startswith('http'):
                link = self._make_absolute(link)

            ts_el = item.select_one('span.timestamp')
            if not ts_el:
                continue  # Skip articles without a real publish time
            published = self._parse_timestamp(ts_el.get_text(strip=True))

            articles.append({
                'title': title, 'link': link,
                'published': published, 'source': self.source,
            })

        return articles

    def _parse_timestamp(self, text: str) -> datetime:
        """Parse 'HH:MM | DD.MM.YY' format."""
        try:
            return self._localize(datetime.strptime(text, '%H:%M | %d.%m.%y'))
        except ValueError:
            pass
        # Fallback: try to extract just a time
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        if m:
            now = self._now()
            return now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return self._now()


class NewsBgScraper(BaseScraper):
    """Scraper for news.bg — fetches article:published_time from article pages."""

    _RELATIVE_RE = re.compile(r'(\d+)\s+(минут|час|ден)')

    def fetch(self) -> list[dict]:
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

            # Use homepage relative time if available
            time_el = topic.select_one('p.time')
            homepage_time = self._parse_relative(time_el.get_text(strip=True)) if time_el else None

            raw.append({'title': title, 'link': link, 'homepage_time': homepage_time})

        # For articles missing time, fetch article pages in parallel
        needs_fetch = [a for a in raw if a['homepage_time'] is None]
        fetched_times = {}
        if needs_fetch:
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


class SegaScraper(RssScraper):
    """Scraper for segabg.com via RSS."""
    pass


# Registry of all scrapers
SCRAPERS = [
    RssScraper('24chasa', 'https://www.24chasa.bg/rss'),
    RssScraper('Dnevnik', 'https://www.dnevnik.bg/rss/'),
    FaktiScraper('Fakti', 'https://fakti.bg/'),
    MediapoolScraper('Mediapool', 'https://www.mediapool.bg/rss'),
    DirBgScraper('Dir.bg', 'https://dir.bg/'),
    NewsBgScraper('News.bg', 'https://news.bg/'),
    SegaScraper('Sega', 'https://segabg.com/rss'),
]


def fetch_all() -> list[dict]:
    """Fetch articles from all sources, classify them, return list of dicts."""
    all_articles = []
    for scraper in SCRAPERS:
        try:
            articles = scraper.fetch()
            logger.info("Fetched %d articles from %s", len(articles), scraper.source)
            all_articles.extend(articles)
        except Exception as e:
            logger.error("Scraper %s failed: %s", scraper.source, e)

    # Classify each article
    for article in all_articles:
        article['category'] = classify(article['title'])

    return all_articles


def save_articles(db, Article, articles: list[dict]) -> int:
    """
    Persist articles to DB using incremental upsert.
    Uses fuzzy string matching to avoid duplicate news with slightly differentiating titles.
    Returns number of newly inserted articles.
    """
    added = 0
    
    # Fetch recent article titles (e.g. last 48 hours to limit memory usage)
    recent_cutoff = datetime.now(SOFIA_TZ) - timedelta(days=2)
    # The database stores naive datetime for published, so remove tzinfo
    recent_cutoff_naive = recent_cutoff.replace(tzinfo=None)
    
    recent_articles = db.session.query(Article.title).filter(
        Article.published >= recent_cutoff_naive
    ).all()
    recent_titles = [a[0] for a in recent_articles]

    for a in articles:
        # Check exact link match
        exists = db.session.query(Article.id).filter_by(link=a['link']).first()
        if exists:
            continue
            
        # Check fuzzy title match
        is_fuzzy_duplicate = False
        new_title = a['title']
        for existing_title in recent_titles:
            # difflib SequenceMatcher returns ratio between 0 and 1
            ratio = difflib.SequenceMatcher(None, new_title, existing_title).ratio()
            if ratio > 0.85: # If 85% similar or more, it's a duplicate
                logger.info("Skipped fuzzy duplicate: '%s' matches '%s' (ratio %.2f)", new_title, existing_title, ratio)
                is_fuzzy_duplicate = True
                break
                
        if is_fuzzy_duplicate:
            continue
            
        # Convert localized datetime to naive for DB storage
        naive_pub = a['published']
        if naive_pub.tzinfo is not None:
            naive_pub = naive_pub.replace(tzinfo=None)

        db.session.add(Article(
            title=new_title,
            link=a['link'],
            published=naive_pub,
            source=a['source'],
            category=a['category'],
        ))
        # Add to local cache to prevent duplicates within the same batch
        recent_titles.append(new_title)
        added += 1

    db.session.commit()
    logger.info("Inserted %d new articles (skipped %d duplicates)", added, len(articles) - added)
    return added
