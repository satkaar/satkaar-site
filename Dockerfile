# Dockerfile pour satkaar-site (vitrine Django).
# Build :   docker build -t satkaar-site:latest .
# Run :     docker run -p 8080:8080 -e DEBUG=false -e ALLOWED_HOSTS=satkaar.fr satkaar-site:latest

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HOME=/tmp \
    DJANGO_WSGI_MODULE=satkaar_site.wsgi

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY . .

RUN chmod +x entrypoint.sh

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
