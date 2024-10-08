from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Article(db.Model):
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    published = db.Column(db.DateTime, nullable=False)
    source = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(20), nullable=True)  

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'published': self.published.isoformat(),
            'source': self.source,
            'category': self.category
        }