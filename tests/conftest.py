import os
import tempfile
from datetime import datetime, timedelta

import pytest

# Point the app at a throwaway database before anything imports it
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'test.db')

import app as app_module  # noqa: E402
from config import SOFIA_TZ  # noqa: E402
from models import db, init_db  # noqa: E402


@pytest.fixture
def app_ctx(monkeypatch):
    """Fresh tables and fetch state for every test."""
    monkeypatch.setattr(app_module, 'last_fetch_at', None)
    monkeypatch.setattr(app_module, 'last_fetch_time', None)
    with app_module.app.app_context():
        db.drop_all()
        init_db()
        yield app_module.app
        db.session.remove()


@pytest.fixture
def client(app_ctx):
    return app_ctx.test_client()


@pytest.fixture
def make_article():
    """Article dict as the scrapers return it (plus category, as fetch_all adds)."""
    def make(title, link, source='Dnevnik', category='politics', minutes_ago=0):
        return {
            'title': title,
            'link': link,
            'source': source,
            'category': category,
            'published': datetime.now(SOFIA_TZ) - timedelta(minutes=minutes_ago),
        }
    return make
