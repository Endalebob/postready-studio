FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip pip install --timeout 120 --retries 5 -r requirements.lock
COPY app ./app
COPY tests ./tests
COPY migrations ./migrations
COPY alembic.ini ./
COPY assets ./assets
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
