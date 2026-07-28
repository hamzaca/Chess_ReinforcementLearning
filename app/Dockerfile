# FastAPI backend image.
# Build from the REPOSITORY ROOT: docker build -f app/Dockerfile .
FROM python:3.12-slim

WORKDIR /code

COPY pyproject.toml README.md ./
COPY app ./app
COPY chess_engine ./chess_engine
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir .

EXPOSE 8000

# Apply migrations, then serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
