variable "organization_id" {
  description = "Scaleway organization ID."
  type        = string
}

variable "project_id" {
  description = "Scaleway project ID qui héberge le container site."
  type        = string
}

variable "dns_project_id" {
  description = "Scaleway project ID owning the DNS zone."
  type        = string
  default     = null
}

variable "region" {
  description = "Scaleway region."
  type        = string
  default     = "fr-par"
}

variable "container_namespace_name" {
  description = "Serverless container namespace name."
  type        = string
  default     = "satkaar-prod"
}

variable "container_name" {
  description = "Nom du container serverless côté Scaleway."
  type        = string
  default     = "website-prod"
}

variable "registry_namespace" {
  description = "Scaleway container registry namespace for images."
  type        = string
  default     = "satkaar-prod"
}

variable "image_name" {
  description = "Nom de l’image dans le Container Registry (ex. website → .../website:latest)."
  type        = string
  default     = "website"
}

variable "image_tag" {
  description = "Container image tag used for deployment."
  type        = string
  default     = "latest"
}

variable "port" {
  description = "Port HTTP exposé par le container."
  type        = number
  default     = 3000
}

variable "cpu_limit" {
  description = "Container CPU limit in millicores."
  type        = number
  default     = 1000
}

variable "memory_limit" {
  description = "Container memory limit in MiB."
  type        = number
  default     = 2048
}

variable "min_scale" {
  description = "Minimum number of container instances."
  type        = number
  default     = 0
}

variable "max_scale" {
  description = "Maximum number of container instances."
  type        = number
  default     = 3
}

variable "max_concurrency" {
  description = "Maximum number of concurrent requests."
  type        = number
  default     = 80
}

variable "timeout" {
  description = "Request timeout in seconds."
  type        = number
  default     = 300
}

variable "domain_zone" {
  description = "Zone DNS du site."
  type        = string
  default     = "satkaar.io"
}

variable "domain_record" {
  description = "Label d’enregistrement sous domain_zone (\"@\" pour l’apex)."
  type        = string
  default     = "@"
}

variable "domain_record_type" {
  description = "Type d’enregistrement DNS (ALIAS pour l’apex chez Scaleway DNS)."
  type        = string
  default     = "ALIAS"
}

variable "manage_dns_record" {
  description = "Whether Terraform should create the DNS record in Scaleway Domains."
  type        = bool
  default     = false
}
