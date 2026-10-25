import os
from zoneinfo import ZoneInfo

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SOFIA_TZ = ZoneInfo('Europe/Sofia')


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'news.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Scraping settings
    FETCH_INTERVAL_MINUTES = 10
    ARTICLES_PER_SOURCE = 60
    REQUEST_TIMEOUT = 15
    REFRESH_COOLDOWN_SECONDS = 60  # min gap between manual /api/refresh fetches
    RETENTION_DAYS = 30  # older articles are deleted after each fetch
    USER_AGENT = (
        "BulgarianNewsAggregator/1.0 "
        "(+https://github.com/dvelkow/real_time_bulgarian_news_aggregator)"
    )
