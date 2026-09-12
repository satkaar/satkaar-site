#!/bin/sh
# Démarrage du conteneur Satkaar.
#   RUN_MODE=web (défaut) : migrations puis gunicorn.
#   RUN_MODE=releve       : relève continue des boîtes mail de l'équipe (second déploiement optionnel).
set -e

mkdir -p "$(dirname "${DJANGO_DB_PATH:-/data/db.sqlite3}")" "${ESPACE_DOCUMENTS_ROOT:-/data/documents_prives}"

if [ "${RUN_MODE:-web}" = "releve" ]; then
    echo "==> Relève des boîtes mail toutes les ${RELEVE_INTERVALLE:-120} s"
    exec python manage.py relever_courriels --boucle "${RELEVE_INTERVALLE:-120}"
fi

if [ "${SKIP_DB_INIT:-false}" != "true" ]; then
    echo "==> Migrations"
    python manage.py migrate --noinput
fi

if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "==> Compte administrateur ${DJANGO_SUPERUSER_EMAIL}"
    python manage.py createsuperuser --noinput \
        --username "${DJANGO_SUPERUSER_USERNAME:-${DJANGO_SUPERUSER_EMAIL%@*}}" \
        --email "${DJANGO_SUPERUSER_EMAIL}" 2>/dev/null \
        && echo "   Compte créé." || echo "   Compte déjà présent."
fi

echo "==> Gunicorn (${DJANGO_WSGI_MODULE}) sur le port ${PORT:-8080}"
exec gunicorn "${DJANGO_WSGI_MODULE}:application" \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout 120 \
    --forwarded-allow-ips "*" \
    --access-logfile - \
    --error-logfile -
