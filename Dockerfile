FROM python:3.13-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi[standard]>=0.115" \
    "jinja2>=3.1" \
    "httpx>=0.27"

COPY ui/ ui/
COPY allecijfers/data/allecijfers.db allecijfers/data/allecijfers.db
COPY allecijfers/data/translations.csv allecijfers/data/translations.csv

ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn ui.main:app --host 0.0.0.0 --port "$PORT"
