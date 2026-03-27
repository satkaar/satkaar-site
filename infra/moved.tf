# Conservent l’état Terraform après renommage frontend → website (pas de destroy).
moved {
  from = scaleway_container_namespace.frontend
  to   = scaleway_container_namespace.website
}

moved {
  from = scaleway_container.frontend
  to   = scaleway_container.website
}

moved {
  from = scaleway_container_domain.frontend_prod
  to   = scaleway_container_domain.website_prod
}

moved {
  from = scaleway_domain_record.frontend_prod_cname
  to   = scaleway_domain_record.website_prod_dns
}
