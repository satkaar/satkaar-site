## Terraform — site de production (satkaar.io)

Ce dossier provisionne les ressources Scaleway pour publier ce site Next.js sur :

- `https://satkaar.io/`

Il crée :

- un namespace Serverless Containers
- le container site (`website-prod` par défaut)
- le domaine personnalisé sur le container
- éventuellement un enregistrement DNS Scaleway (`manage_dns_record = true`)

L’image registry par défaut est **`website`** (`satkaar-prod/website:latest`), alignée avec GitHub Actions.

## Prérequis

- Terraform >= 1.5
- Compte Scaleway et identifiants API
- Zone DNS `satkaar.io` chez Scaleway Domains **uniquement** si `manage_dns_record = true`

```bash
export SCW_ACCESS_KEY="..."
export SCW_SECRET_KEY="..."
```

## Configuration

```bash
cp terraform.tfvars.example terraform.tfvars
```

Renseigner notamment : `project_id`, `organization_id`, et `dns_project_id` si besoin.

## Déploiement

```bash
terraform init
terraform plan
terraform apply
```

DNS hors Scaleway : garder `manage_dns_record = false` et gérer les enregistrements chez le registrar (voir `script/new-dns.sh` pour OVH + apex en A/AAAA).

## Outputs utiles

- `website_container_id` → secret GitHub **`SCW_WEBSITE_CONTAINER_ID`** (remplacer l’ancien `SCW_FRONTEND_CONTAINER_ID` par la même valeur)
- `website_registry_image` → doit correspondre à `rg.../satkaar-prod/website:latest`
- `website_container_domain`, `website_public_url`

### Erreur `409 Domain already exist` sur `scaleway_container_domain`

Réaligner l’état avec le domaine existant sur Scaleway :

```bash
terraform state rm 'scaleway_container_domain.website_prod'
terraform import -var-file=terraform.tfvars 'scaleway_container_domain.website_prod' 'fr-par/DOMAIN_UUID'
```

`DOMAIN_UUID` : `scw container domain list region=fr-par -o json | jq`.
