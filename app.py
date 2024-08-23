from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, Article
from data_ingestion.fetch_news import NewsAggregator
from spark_processes import run_spark_processing
import schedule
import time
import threading

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
CORS(app)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 60  
    
    all_articles = Article.query.order_by(Article.published.desc()).all()
    
    politics = [a for a in all_articles if a.category == 'politics']
    sports = [a for a in all_articles if a.category == 'sports']
    others = [a for a in all_articles if a.category == 'others']
    
    total_articles = len(all_articles)
    total_pages = (total_articles + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    
    politics_page = politics[start:end]
    sports_page = sports[start:end]
    others_page = others[start:end]
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total_articles,
        'pages': total_pages
    }
    
    return render_template('index.html', politics=politics_page, sports=sports_page, others=others_page, pagination=pagination)

@app.route('/news', methods=['GET'])
def get_news():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 60, type=int)
        all_articles = Article.query.order_by(Article.published.desc()).all()
        
        total_articles = len(all_articles)
        total_pages = (total_articles + per_page - 1) // per_page
        
        start = (page - 1) * per_page
        end = start + per_page
        
        articles_page = all_articles[start:end]
        
        return jsonify({
            'articles': [article.to_dict() for article in articles_page],
            'total': total_articles,
            'pages': total_pages,
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
                source=article_data[3],
                category=article_data[4]
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

    with app.app_context():
        NewsAggregator.update_news_database()

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(debug=True, use_reloader=False)