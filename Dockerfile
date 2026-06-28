FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_CONFIG_PATH=/data/config.json

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY translations ./translations
RUN mkdir -p /data
EXPOSE 5001
CMD ["python", "-m", "app.main"]
