FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# SQLite lives on a volume so articles survive container restarts
ENV DATABASE_URL=sqlite:////data/news.db
VOLUME /data
EXPOSE 8000

# One worker: the SSE client list and the fetch scheduler live in this process.
# Each open browser tab holds one thread for its SSE stream.
CMD ["gunicorn", "--workers", "1", "--threads", "32", "--bind", "0.0.0.0:8000", "wsgi:app"]
