FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-por \
        tesseract-ocr-eng \
        ffmpeg \
        gettext \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic/compilemessages only need a placeholder secret key; the
# real one is injected by Render at runtime and never baked into the image.
RUN DJANGO_SECRET_KEY=build-time-placeholder python manage.py compilemessages \
    && DJANGO_SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput \
    && mkdir -p media \
    && chown -R app:app /app

USER app

EXPOSE 10000
CMD gunicorn doc4ai.wsgi --bind 0.0.0.0:${PORT:-10000} --timeout 90 --log-file -
