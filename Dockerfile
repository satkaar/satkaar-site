# Image de production du site Satkaar (vitrine + espace client), servie sur https://satkaar.io
# par la plateforme Kapsule (Ingress NGINX + Let's Encrypt, chart Helm django-app).
#
#   docker build -t satkaar-site .
#   docker run -p 8080:8080 -e DEBUG=False -e ALLOWED_HOSTS=localhost \
#     -e DJANGO_SECRET_KEY=... -v satkaar-data:/data satkaar-site
#
# Contrat avec la plateforme : écoute sur $PORT (8080), variables DEBUG / ALLOWED_HOSTS /
# SITE_URL / GUNICORN_WORKERS, secrets par l'environnement, données sur /data.

# ── Étape 1 : dépendances compilées en wheels ────────────────────────────────
FROM python:3.14-slim AS construction

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Étape 2 : image finale, sans outils de compilation ───────────────────────
FROM python:3.14-slim

ARG DJANGO_WSGI_MODULE=maquette.wsgi
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    HOME=/tmp \
    DJANGO_WSGI_MODULE=${DJANGO_WSGI_MODULE} \
    DEBUG=False \
    DJANGO_PROXY_DE_CONFIANCE=true \
    DJANGO_DB_PATH=/data/db.sqlite3 \
    ESPACE_DOCUMENTS_ROOT=/data/documents_prives

WORKDIR /app

RUN apt-get update \
    && apt-get -y upgrade \
    && rm -rf /var/lib/apt/lists/*

COPY --from=construction /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

COPY . .

# Fichiers statiques versionnés et compressés dès la construction de l'image : le démarrage
# du conteneur reste rapide. La clé factice ne sert qu'à cette commande.
RUN DJANGO_SECRET_KEY=construction-uniquement python manage.py collectstatic --noinput \
    && chmod +x entrypoint.sh

# Utilisateur sans privilèges ; /data accueille la base et les fichiers privés (volume).
RUN addgroup --system --gid 1001 satkaar \
    && adduser --system --uid 1001 --ingroup satkaar satkaar \
    && mkdir -p /data \
    && chown -R satkaar:satkaar /data /app
USER satkaar

VOLUME ["/data"]
EXPOSE 8080

# Le port répond : gunicorn est démarré (même principe que les sondes TCP du chart).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os, socket; socket.create_connection(('127.0.0.1', int(os.environ.get('PORT', 8080))), 3)"

ENTRYPOINT ["./entrypoint.sh"]
