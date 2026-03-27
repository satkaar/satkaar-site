output "website_registry_image" {
  description = "Image registry utilisée par le container site."
  value       = local.website_registry_image
}

output "website_container_id" {
  description = "ID Scaleway (secret GitHub SCW_WEBSITE_CONTAINER_ID)."
  value       = scaleway_container.website.id
}

output "website_container_domain" {
  description = "Nom de domaine Scaleway par défaut du container."
  value       = scaleway_container.website.domain_name
}

output "website_public_url" {
  description = "URL publique attendue."
  value       = var.domain_record == "@" ? "https://${var.domain_zone}" : "https://${var.domain_record}.${var.domain_zone}"
}
