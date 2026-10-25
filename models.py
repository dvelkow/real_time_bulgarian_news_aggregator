import sqlite3
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine

from config import SOFIA_TZ

db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def _sqlite_setup(dbapi_conn, _record):
    """SQLite's built-in lower() only folds ASCII, so ilike() missed 'Борисов' for 'борисов'.
    Replace it with Python's Unicode-aware lower() on every SQLite connection, and use WAL
    so page requests can read while the background fetch writes."""
    if isinstance(dbapi_conn, sqlite3.Connection):
        dbapi_conn.create_function(
            'lower', 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True,
        )
        cursor = dbapi_conn.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.close()


def format_published(published: datetime) -> str:
    """Display time: '14:20' today, 'вчера 14:20', otherwise '23.10 14:20'."""
    today = datetime.now(SOFIA_TZ).date()
    if published.date() == today:
        return published.strftime('%H:%M')
    if published.date() == today - timedelta(days=1):
        return published.strftime('вчера %H:%M')
    return published.strftime('%d.%m %H:%M')


class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), nullable=False, unique=True, index=True)
    published = db.Column(db.DateTime, nullable=False, index=True)  # naive, Europe/Sofia
    source = db.Column(db.String(50), nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False, default='other', index=True)
    # Same story from another source: kept, and shown under the original as "също в"
    duplicate_of = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=True, index=True)

    duplicates = db.relationship(
        'Article', backref=db.backref('original', remote_side=[id]), order_by='Article.published',
    )

    def __repr__(self):
        return f"<Article {self.source}: {self.title[:50]}>"

    @property
    def published_iso(self) -> str:
        return self.published.replace(tzinfo=SOFIA_TZ).isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'published': self.published_iso,
            'time_label': format_published(self.published),
            'source': self.source,
            'category': self.category,
            'duplicate_of': self.duplicate_of,
            'also_in': [{'source': d.source, 'link': d.link} for d in self.duplicates],
        }


def init_db():
    """Create tables, and add columns introduced after the first release
    (create_all() never alters an existing table)."""
    db.create_all()
    columns = {c['name'] for c in inspect(db.engine).get_columns('articles')}
    if 'duplicate_of' not in columns:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE articles ADD COLUMN duplicate_of INTEGER REFERENCES articles(id)'))
            conn.execute(text('CREATE INDEX ix_articles_duplicate_of ON articles (duplicate_of)'))
