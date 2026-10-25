import sqlite3

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def _unicode_lower(dbapi_conn, _record):
    """SQLite's built-in lower() only folds ASCII, so ilike() missed 'Борисов' for 'борисов'.
    Replace it with Python's Unicode-aware lower() on every SQLite connection."""
    if isinstance(dbapi_conn, sqlite3.Connection):
        dbapi_conn.create_function(
            'lower', 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True,
        )


class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), nullable=False, unique=True, index=True)
    published = db.Column(db.DateTime, nullable=False, index=True)
    source = db.Column(db.String(50), nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False, default='other', index=True)

    def __repr__(self):
        return f"<Article {self.source}: {self.title[:50]}>"

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'published': self.published.isoformat(),
            'source': self.source,
            'category': self.category,
        }
