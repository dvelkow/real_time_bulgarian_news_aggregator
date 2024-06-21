import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from models import db, Article
from data_ingestion.fetch_news import fetch_news
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Load environment variables
load_dotenv()

# Debug prints
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print(f"DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD'))}") # Mask the password

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Debug print for database URI
print(f"SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Initialize extensions
db.init_app(app)
CORS(app)

@app.route('/news', methods=['GET'])
def get_news():
    try:
        articles = Article.query.order_by(Article.published.desc()).limit(10).all()
        return jsonify([{
            'id': article.id,
            'title': article.title,
            'link': article.link,
            'published': article.published.isoformat(),
            'source': article.source
        } for article in articles])
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/fetch-news', methods=['GET'])
def fetch_news_route():
    try:
        new_articles = fetch_news()
        added_count = 0
        for article_data in new_articles:
            existing_article = Article.query.filter_by(link=article_data[1]).first()
            if not existing_article:
                article = Article(
                    title=article_data[0],
                    link=article_data[1],
                    published=article_data[2],
                    source=article_data[3]
                )
                db.session.add(article)
                added_count += 1
        db.session.commit()
        return jsonify({"message": f"Successfully fetched {len(new_articles)} articles. Added {added_count} new articles."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error fetching new articles: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test_route():
    return jsonify({"message": "Test route is working"}), 200

def scheduled_fetch_news():
    with app.app_context():
        fetch_news_route()

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=scheduled_fetch_news,
    trigger=IntervalTrigger(hours=1),
    id='fetch_news_job',
    name='Fetch news every hour',
    replace_existing=True)

atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    app.run(debug=True)
    
    
    
    