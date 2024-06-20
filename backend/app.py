from flask import Flask, jsonify
from flask_cors import CORS
from models import db, Article
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
CORS(app)

@app.route('/news', methods=['GET'])
def get_news():
    try:
        articles = Article.query.order_by(Article.published.desc()).limit(10).all()
        print(f"Fetched articles: {articles}")  
        return jsonify([article.to_dict() for article in articles])
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return jsonify({"error": "Error fetching articles"}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
