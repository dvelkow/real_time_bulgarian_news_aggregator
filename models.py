from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
