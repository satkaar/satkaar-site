#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/.env"
  set +a
fi

DOMAIN="satkaar.io"
INFRA_DIR="${SCRIPT_DIR}/../infra"

# Plusieurs hôtes si le DNS Scaleway (nom du container) ne correspond pas encore au Terraform.
collect_scaleway_host_candidates() {
  [[ -n "${TARGET:-}" ]] && echo "${TARGET%.}"
  if command -v terraform >/dev/null 2>&1; then
    terraform -chdir="${INFRA_DIR}" output -raw website_container_domain 2>/dev/null || true
  fi
  local cid="${SCW_WEBSITE_CONTAINER_ID:-${SCW_FRONTEND_CONTAINER_ID:-}}"
  if command -v scw >/dev/null 2>&1 && [[ -n "${cid}" ]]; then
    scw container container get "${cid}" region="${SCW_REGION:-fr-par}" -o json 2>/dev/null | jq -r '.domain_name // empty' || true
  fi
  echo "satkaarprodut0tyll8-website-prod.functions.fnc.fr-par.scw.cloud"
  echo "satkaarprodut0tyll8-frontend-prod.functions.fnc.fr-par.scw.cloud"
}

try_resolve_ipv4() {
  local host="$1"
  host="${host%.}"
  [[ -z "$host" ]] && return 1
  dig +short "$host" A | grep -E '^[0-9.]+$' || true
}

echo "== Choisir le hostname Scaleway résolvable (dig A) =="
RESOLVED_HOST=""
IPV4S=""
IPV6S=""
seen=""
while IFS= read -r cand; do
  [[ -z "$cand" ]] && continue
  case " $seen " in *" $cand "*) continue ;; esac
  seen+=" $cand "
  hits=$(try_resolve_ipv4 "$cand" | head -1 || true)
  if [[ -n "${hits}" ]]; then
    RESOLVED_HOST="${cand%.}"
    IPV4S=$(try_resolve_ipv4 "$cand" || true)
    IPV6S=$(dig +short "${RESOLVED_HOST}" AAAA | grep -E ':' || true)
    echo "OK → ${RESOLVED_HOST} (IPv4: $(echo "$IPV4S" | tr '\n' ' '))"
    break
  fi
  echo "SKIP (pas d’A) → ${cand}"
done < <(collect_scaleway_host_candidates)

if [[ -z "${IPV4S}" ]]; then
  echo "::error::Aucun hostname Scaleway ne résout en IPv4. Vérifie terraform apply / nom du container, ou export TARGET=nom.functions.fnc.fr-par.scw.cloud" >&2
  exit 1
fi

OVH_AK="${TF_VAR_ovh_application_key:?Set TF_VAR_ovh_application_key in script/.env}"
OVH_AS="${TF_VAR_ovh_application_secret:?Set TF_VAR_ovh_application_secret in script/.env}"
OVH_CK="${TF_VAR_ovh_consumer_key:?Set TF_VAR_ovh_consumer_key in script/.env}"
OVH_ENDPOINT="${TF_VAR_ovh_endpoint:-ovh-eu}"

case "$OVH_ENDPOINT" in
  ovh-eu) BASE="https://eu.api.ovh.com/1.0" ;;
  ovh-ca) BASE="https://ca.api.ovh.com/1.0" ;;
  kimsufi-eu) BASE="https://eu.api.kimsufi.com/1.0" ;;
  soyoustart-eu) BASE="https://eu.api.soyoustart.com/1.0" ;;
  *) BASE="https://eu.api.ovh.com/1.0" ;;
esac

ovh_call() {
  local method="$1"; shift
  local path="$1"; shift
  local body="${1:-}"
  local ts sig
  ts=$(curl -s "$BASE/auth/time")
  sig=$(printf "%s+%s+%s+%s+%s+%s" "$OVH_AS" "$OVH_CK" "$method" "${BASE}${path}" "$body" "$ts" | sha1sum | awk '{print $1}')
  sig="\$1\$${sig}"

  curl -sS -X "$method" "${BASE}${path}" \
    -H "X-Ovh-Application: $OVH_AK" \
    -H "X-Ovh-Consumer: $OVH_CK" \
    -H "X-Ovh-Timestamp: $ts" \
    -H "X-Ovh-Signature: $sig" \
    -H "Content-Type: application/json" \
    ${body:+--data "$body"}
}

ovh_fail_if_error() {
  local resp="$1"
  if echo "$resp" | jq -e '.class != null' >/dev/null 2>&1; then
    echo "::error::OVH API error: $resp" >&2
    return 1
  fi
  return 0
}

echo "== List records =="
RECORD_IDS=$(ovh_call GET "/domain/zone/${DOMAIN}/record")
echo "$RECORD_IDS"

echo "== Remove existing apex A / AAAA (racine ${DOMAIN} seulement) =="
for id in $(echo "$RECORD_IDS" | jq -r '.[]'); do
  rec=$(ovh_call GET "/domain/zone/${DOMAIN}/record/${id}")
  if echo "$rec" | jq -e '
    (.fieldType == "A" or .fieldType == "AAAA")
    and ((.subDomain == "") or (.subDomain == null))
  ' >/dev/null 2>&1; then
    echo "Deleting apex $(echo "$rec" | jq -r .fieldType) id=${id} target=$(echo "$rec" | jq -r .target)"
    ovh_call DELETE "/domain/zone/${DOMAIN}/record/${id}" >/dev/null || true
  fi
done

echo "== Create apex A (→ ${RESOLVED_HOST}) =="
while IFS= read -r ip; do
  [[ -z "$ip" ]] && continue
  BODY=$(jq -nc --arg target "$ip" --argjson ttl 300 '{fieldType:"A", subDomain:"", target:$target, ttl:$ttl}')
  RESP=$(ovh_call POST "/domain/zone/${DOMAIN}/record" "$BODY")
  echo "$RESP"
  ovh_fail_if_error "$RESP" || exit 1
done <<< "${IPV4S}"

if [[ -n "${IPV6S}" ]]; then
  echo "== Create apex AAAA (optionnel) =="
  while IFS= read -r ip6; do
    [[ -z "$ip6" ]] && continue
    BODY=$(jq -nc --arg target "$ip6" --argjson ttl 300 '{fieldType:"AAAA", subDomain:"", target:$target, ttl:$ttl}')
    RESP=$(ovh_call POST "/domain/zone/${DOMAIN}/record" "$BODY")
    echo "$RESP"
    if echo "$RESP" | jq -e '.class != null' >/dev/null 2>&1; then
      echo "::warning::AAAA ignoré pour ${ip6}: $RESP" >&2
    fi
  done <<< "${IPV6S}"
fi

echo "== Refresh zone =="
ovh_call POST "/domain/zone/${DOMAIN}/refresh" "{}"

echo "Done."
