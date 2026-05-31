FROM python:3.13-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi[standard]==0.136.1" \
    "jinja2==3.1.6" \
    "httpx==0.28.1" \
 && adduser --disabled-password --gecos "" appuser \
 && chown appuser /app

USER appuser

COPY ui/ ui/
COPY allecijfers/data/allecijfers.db allecijfers/data/allecijfers.db
COPY allecijfers/data/translations.csv allecijfers/data/translations.csv

ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn ui.main:app --host 0.0.0.0 --port "$PORT"
