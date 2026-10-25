"""
Production entry point:

    gunicorn --workers 1 --threads 32 --bind 0.0.0.0:8000 wsgi:app

Keep a single worker and no --preload: the SSE client list and the fetch scheduler
live in this process. Each open browser tab holds one thread for its SSE stream.
"""

from app import app, start_background_jobs

start_background_jobs()
