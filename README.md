# Satkaar — maquette du site

Site vitrine de Satkaar, éditeur de logiciels de relation citoyen pour les
collectivités. Projet Django, sans dépendance externe : polices, styles et
scripts sont auto-hébergés.

## Démarrer

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Le site est alors sur http://127.0.0.1:8000/.

## Arborescence des pages

| URL | Gabarit | Contenu |
| --- | --- | --- |
| `/` | `templates/pages/accueil.html` | Héros, trois piliers, territoire, verbatims, appel à l'action |
| `/nos-solutions/` | `pages/solutions.html` | Marine, Vanessa, trois cas d'usage |
| `/conseil-et-accompagnement/` | `pages/conseil.html` | Cadrage, reprise, formation, suivi, expertise |
| `/souverainete-et-conformite/` | `pages/souverainete.html` | Cinq engagements, pièces remises |
| `/references/` | `pages/references.html` | Forcalquier, Manosque, carte des déploiements |
| `/a-propos/` | `pages/a_propos.html` | Constat, équipe, labels |
| `/contact/` | `pages/contact.html` | Formulaire de démonstration, coordonnées |
| `/mentions-legales/` | `legal/mentions_legales.html` | |
| `/politique-de-confidentialite/` | `legal/confidentialite.html` | |
| `/declaration-d-accessibilite/` | `legal/accessibilite.html` | Format imposé par le RGAA |
| `/conditions-generales-d-utilisation/` | `legal/cgu.html` | |

Le texte vit dans les gabarits : pour corriger une formulation, on édite le
gabarit, pas du code Python.

## Structure du projet

| | |
| --- | --- |
| `maquette/` | Réglages, routage, WSGI/ASGI |
| `pages/` | Vues, formulaire et modèle des demandes de démonstration |
| `templates/base.html` | En-tête, pied de page, métadonnées |
| `templates/partials/` | Signe de marque, pied de page, champ de formulaire |
| `static/css/site.css` | Feuille de style unique, commentée par section |
| `static/css/fonts.css` | Déclarations `@font-face` des polices auto-hébergées |
| `static/fonts/` | 6 fichiers woff2 (latin et latin-ext), ~210 Ko |

## Demandes de démonstration

Le formulaire de contact enregistre chaque demande en base
(`pages.DemandeDemonstration`) et elle est consultable dans l'admin Django,
avec une case « traitée ». Aucun courriel n'est envoyé pour l'instant.

```bash
python manage.py createsuperuser   # puis /admin/
```

## Charte

| Jeton CSS | Valeur | Usage |
| --- | --- | --- |
| `--bleu-nuit` | `#0E2C4B` | Texte courant, héros, pied de page |
| `--bleu-institution` | `#1E63A8` | Liens, boutons de contour |
| `--terre` | `#D96A34` | Filets, puces, accents — **jamais** de texte sur fond clair |
| `--terre-fonce` | `#BE5620` | Fond des boutons primaires (blanc sur terre : 4,6:1) |
| `--olivier` | `#3F8F7A` | Badges « en production », pastilles de preuve |
| `--pierre` | `#F6F3EE` | Fonds de section alternés |
| `--ardoise` | `#5C6672` | Texte secondaire |

Typographie : Instrument Sans (titres), Inter (texte), JetBrains Mono (chiffres
et badges), sous licence SIL Open Font License 1.1.

## Avant la mise en ligne

Les mentions `à confirmer`, `à recueillir`, `à rédiger avec la commune` sont
rendues par la classe CSS `.jalon` — un encadré terre cuite en pointillés, bien
visible. Pour toutes les lister :

```bash
grep -rn 'class="jalon"' templates/
```

Chaque jalon doit être remplacé par une information vérifiée, ou retiré. Le
style `.jalon` peut ensuite être supprimé de `static/css/site.css`.

## Réglages pilotés par l'environnement

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | clé de développement | **Obligatoire** en production |
| `DJANGO_DEBUG` | `1` | `0` en production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Domaines séparés par des virgules |

Langue et fuseau : `fr-fr`, `Europe/Paris`.
