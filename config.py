import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'news.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Scraping settings
    FETCH_INTERVAL_MINUTES = 10
    ARTICLES_PER_SOURCE = 60
    REQUEST_TIMEOUT = 15
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
