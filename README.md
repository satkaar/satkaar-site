# Satkaar — site vitrine

Site corporate Django pour **Satkaar SAS**, éditeur français de logiciels pour les
communes. Mono-page (`/`) avec ancres `#qui-sommes-nous`, `#mission`, `#confiance`,
`#ia-souveraine`, `#contact`, plus une page `mentions-legales/`.

Stack : **Django 6 · Python 3.12 · WhiteNoise · PostgreSQL (prod) / SQLite (dev)**.

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Site : http://127.0.0.1:8000/
- Admin (messages de contact) : http://127.0.0.1:8000/admin/
- sitemap.xml et robots.txt sont auto-générés sur `/sitemap.xml` et `/robots.txt`.

## Variables d'environnement

| Variable | Défaut | Description |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | clé dev | À renouveler en prod |
| `DEBUG` | `true` | Mode debug |
| `ALLOWED_HOSTS` | _(vide en debug)_ | Hôtes autorisés, séparés par virgules |
| `SITE_URL` | `https://satkaar.fr` | URL canonique (sitemap, Open Graph) |
| `DATABASE_URL` | sqlite local | URL Postgres en prod |
| `EMAIL_BACKEND` | `console` | `django.core.mail.backends.smtp.EmailBackend` en prod |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | _(vides)_ | Config SMTP |
| `DEFAULT_FROM_EMAIL` | `noreply@satkaar.fr` | Expéditeur des notifications |
| `CONTACT_NOTIFICATION_EMAIL` | `contact@satkaar.fr` | Destinataire des messages de contact |

## Formulaire de contact

Les soumissions sont **stockées en base** (modèle `MessageContact`, consultable
dans l'admin Django) **et notifiées par email** à `CONTACT_NOTIFICATION_EMAIL`.

Anti-spam : champ honeypot caché (`site_web`) + consentement RGPD explicite
obligatoire + CSRF Django natif.

## Déploiement Docker

```bash
docker build -t satkaar-site:latest .
docker run --rm -p 8080:8080 \
  -e DEBUG=false \
  -e ALLOWED_HOSTS=satkaar.fr \
  -e SITE_URL=https://satkaar.fr \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
  -e EMAIL_HOST=smtp.scaleway.com \
  -e EMAIL_HOST_USER=... \
  -e EMAIL_HOST_PASSWORD=... \
  satkaar-site:latest
```

L'`entrypoint.sh` enchaîne `collectstatic` + `migrate` puis lance Gunicorn sur
le port 8080. Prévu pour **Scaleway Serverless Containers** (ou Cloud Run, ou
Kapsule pour mutualisation avec le reste de la plateforme).

## Performance & accessibilité

- CSS custom (pas de Tailwind CDN) → bundle < 15 ko gzippé.
- 2 polices Google Fonts en `display=swap`.
- WhiteNoise + `CompressedManifestStaticFilesStorage` → static cache-busting.
- Skip-link, focus visibles, contraste AA, alt sur visuels SVG.
- Sitemap + `robots.txt` exposés en racine.

## Arborescence

```
satkaar-site/
├── manage.py
├── requirements.txt
├── Dockerfile
├── entrypoint.sh
├── .env.example
├── satkaar_site/         # settings / urls / wsgi
├── vitrine/              # app principale
│   ├── models.py         # MessageContact
│   ├── forms.py          # ContactForm (honeypot, RGPD)
│   ├── views.py          # Home, MentionsLegales, robots
│   ├── sitemaps.py
│   ├── urls.py
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── partials/{header,footer}.html
│   ├── home.html         # 6 sections en mono-page
│   └── mentions_legales.html
└── static/{css,js,img}
```
