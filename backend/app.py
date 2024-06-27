import os
import sys
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, Article
from data_ingestion.fetch_news import NewsAggregator
from spark_processes import run_spark_processing
import schedule
import time
import threading

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
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        articles = Article.query.order_by(Article.published.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'articles': [article.to_dict() for article in articles.items],
            'total': articles.total,
            'pages': articles.pages,
            'current_page': page
        })
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/fetch-news', methods=['GET'])
def fetch_news_route():
    try:
        new_articles = NewsAggregator.fetch_all_news()
        for article_data in new_articles:
            article = Article(
                title=article_data[0],
                link=article_data[1],
                published=article_data[2],
                source=article_data[3]
            )
            db.session.add(article)
        db.session.commit()
        return jsonify({"message": f"Successfully fetched {len(new_articles)} new articles"}), 200
    except Exception as e:
        print(f"Error fetching new articles: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test_route():
    return jsonify({"message": "Test route is working"}), 200

def run_scheduled_task():
    with app.app_context():
        print("Running scheduled task to update news...")
        NewsAggregator.update_news_database()

def run_scheduler():
    schedule.every(10).minutes.do(run_scheduled_task)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    # Run initial news fetch
    with app.app_context():
        NewsAggregator.update_news_database()

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # This ensures the thread will exit when the main program does
    scheduler_thread.start()

    app.run(debug=True, use_reloader=False)