# Déploiement sur https://satkaar.io

Le site tourne sur la plateforme Kubernetes mutualisée **satkaar/platform** (Scaleway Kapsule) :
Ingress NGINX + certificat Let's Encrypt, chart Helm générique `django-app`, image dans le
registre `rg.fr-par.scw.cloud/mairie-agglo-platform/satkaar-site`. C'est la même chaîne que
l'ancienne vitrine (dépôt satkaar/satkaar-site), qu'elle remplace.

## L'image

- `Dockerfile` : Python 3.14, dépendances en wheels, fichiers statiques versionnés et
  compressés à la construction (WhiteNoise), utilisateur sans privilèges (uid 1001), port 8080.
- `entrypoint.sh` : migrations puis gunicorn. `RUN_MODE=releve` lance à la place la relève
  continue des boîtes mail (second déploiement facultatif).
- Données sur **/data** : base SQLite (`/data/db.sqlite3`) et fichiers privés
  (`/data/documents_prives` : documents clients, pièces jointes du Mail).

Essai en local :

```sh
docker build -t satkaar-site .
docker run -p 8080:8080 -e DEBUG=False -e ALLOWED_HOSTS=localhost \
  -e DJANGO_SECRET_KEY=$(openssl rand -hex 32) -e SECURE_SSL_REDIRECT=false \
  -v satkaar-data:/data satkaar-site
```

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DEBUG` | `False` en production (défaut de l'image). |
| `ALLOWED_HOSTS` | `satkaar.io` (plusieurs : séparés par des virgules). |
| `SITE_URL` | `https://satkaar.io` : origine de confiance des formulaires. |
| `DJANGO_SECRET_KEY` | **Secret.** Obligatoire ; ne pas la changer ensuite (sessions, mots de passe des boîtes mail). |
| `COURRIEL_CLE` | **Secret.** Clé Fernet des mots de passe des boîtes mail (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`). |
| `ANTHROPIC_API_KEY` | **Secret.** Reformulation par l'IA du formulaire de contact. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER` | Serveur d'envoi (OVH : `ssl0.ovh.net`, `465`, `true`). |
| `EMAIL_HOST_PASSWORD` | **Secret.** Mot de passe de la boîte d'envoi. |
| `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` | Facultatif : crée le premier compte administrateur au démarrage. |
| `DATABASE_URL` | Facultatif : bascule sur Postgres au lieu de SQLite. |

## Première mise en production

1. **Valeurs Helm** — remplacer `helm/values/satkaar-site.yaml` du dépôt satkaar/platform par
   `deploiement/satkaar-site.values.yaml` : volume persistant sur /data, `fsGroup: 1001`,
   stratégie `Recreate`, variables ci-dessus. Sans volume, les données seraient perdues à chaque
   déploiement.
2. **Secret Kubernetes** (complète celui qui existe déjà) :
   ```sh
   kubectl -n satkaar-site create secret generic satkaar-site-secrets \
     --from-literal=DJANGO_SECRET_KEY=... --from-literal=COURRIEL_CLE=... \
     --from-literal=ANTHROPIC_API_KEY=... --from-literal=EMAIL_HOST_PASSWORD=... \
     --dry-run=client -o yaml | kubectl apply -f -
   ```
   Garder la valeur actuelle de `DJANGO_SECRET_KEY` si elle existe déjà.
3. **Dépôt GitHub** — le workflow `.github/workflows/deploy.yml` appelle le déploiement commun de
   satkaar/platform. Il lui faut, dans ce dépôt : les secrets `SCW_ACCESS_KEY` et
   `SCW_SECRET_KEY`, les variables `SCW_DEFAULT_PROJECT_ID` et `SCW_DEFAULT_ORGANIZATION_ID`, et
   les environnements `preprod` et `production`.
4. **Déployer** — pousser sur la branche `preprod` (https://preprod.satkaar.io), vérifier, puis
   lancer le workflow à la main avec `prod`.
5. **DNS** — l'apex `satkaar.io` a aujourd'hui deux enregistrements A : `51.15.139.157` (la
   plateforme) et `213.186.33.5` (hébergement OVH, sans HTTPS). Supprimer le second dans la zone
   OVH, sinon une partie des visiteurs tombe sur une erreur de certificat.
6. **Après le premier démarrage** — créer les comptes de l'équipe (`is_staff`) et reconnecter les
   boîtes mail dans l'espace (Mail › Gérer les boîtes).

## Sauvegardes

Tout l'état du site est dans le volume /data. Copie ponctuelle :

```sh
kubectl -n satkaar-site exec deploy/satkaar-site -- \
  python -c "import sqlite3; s=sqlite3.connect('/data/db.sqlite3'); d=sqlite3.connect('/data/sauvegarde.sqlite3'); s.backup(d)"
kubectl -n satkaar-site cp satkaar-site-<pod>:/data/sauvegarde.sqlite3 ./sauvegarde.sqlite3
```
