from flask import Flask, jsonify
from flask_cors import CORS
from models import db, Article
from config import Config  # Ensure this line is correct

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
CORS(app)

@app.route('/news', methods=['GET'])
def get_news():
    articles = Article.query.order_by(Article.published.desc()).limit(10).all()
    return jsonify([article.to_dict() for article in articles])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
