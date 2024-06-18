import feedparser
from models import db, Article

def fetch_news():
    sources = [
        'https://example.com/rss',  # Replace with actual RSS feeds
        'https://another-example.com/rss'
    ]

    for source in sources:
        feed = feedparser.parse(source)
        for entry in feed.entries:
            if not Article.query.filter_by(link=entry.link).first():
                article = Article(
                    title=entry.title,
                    link=entry.link,
                    published=entry.published,
                    source=source
                )
                db.session.add(article)
                db.session.commit()
