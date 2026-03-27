locals {
  website_registry_image = "rg.${var.region}.scw.cloud/${var.registry_namespace}/${var.image_name}:${var.image_tag}"
  website_hostname       = var.domain_record == "@" ? var.domain_zone : "${var.domain_record}.${var.domain_zone}"
}

resource "scaleway_container_namespace" "website" {
  name       = var.container_namespace_name
  project_id = var.project_id
  region     = var.region
}

resource "scaleway_container" "website" {
  name           = var.container_name
  namespace_id   = scaleway_container_namespace.website.id
  region         = var.region
  registry_image = local.website_registry_image

  description     = "Production website for satkaar.io"
  port            = var.port
  cpu_limit       = var.cpu_limit
  memory_limit    = var.memory_limit
  min_scale       = var.min_scale
  max_scale       = var.max_scale
  max_concurrency = var.max_concurrency
  timeout         = var.timeout
  privacy         = "public"
  protocol        = "http1"
}

resource "scaleway_container_domain" "website_prod" {
  container_id = scaleway_container.website.id
  hostname     = local.website_hostname
}

resource "scaleway_domain_record" "website_prod_dns" {
  count      = var.manage_dns_record ? 1 : 0
  project_id = var.dns_project_id
  dns_zone   = var.domain_zone
  name       = var.domain_record
  type       = var.domain_record_type
  ttl        = 300
  data       = scaleway_container.website.domain_name

  depends_on = [scaleway_container_domain.website_prod]
}
