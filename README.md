# site-maquette

Projet Django, prêt à recevoir une maquette de site.

## Démarrer

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Le site est alors sur http://127.0.0.1:8000/.

## Structure

| | |
| --- | --- |
| `maquette/` | Réglages, routage, WSGI/ASGI |
| `templates/` | Gabarits partagés (déjà déclaré dans `TEMPLATES`) |
| `static/` | CSS, images, scripts (déjà déclaré dans `STATICFILES_DIRS`) |

## Réglages pilotés par l'environnement

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | clé de développement | **Obligatoire** en production |
| `DJANGO_DEBUG` | `1` | `0` en production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Domaines séparés par des virgules |

Langue et fuseau : `fr-fr`, `Europe/Paris`.

## Étapes suivantes

Rien n'est encore créé côté application : ni app, ni modèle, ni gabarit.
`python manage.py startapp <nom>` pour démarrer.
