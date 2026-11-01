#!/usr/bin/env bash
# Lê chaves do Bitwarden Secrets Manager (pelo nome) e exporta para os próximos passos do job, mascaradas.
# Ambiente: BWS_ACCESS_TOKEN, CHAVES (nomes separados por espaço ou linha), BWS_SERVER_URL (opcional) e
# BWS (opcional, caminho de um bws já instalado; sem ele, baixa a CLI oficial e confere o checksum).
set -euo pipefail

: "${BWS_ACCESS_TOKEN:?falta o secret BITWARDEN_ACCESS_TOKEN no repositório (Settings > Secrets and variables > Actions)}"
: "${CHAVES:?nenhuma chave pedida}"
: "${GITHUB_ENV:?rodar dentro do GitHub Actions}"

pasta=$(mktemp -d)
trap 'rm -rf "$pasta"' EXIT

if [ -z "${BWS:-}" ]; then
  versao=2.1.0
  zip="bws-x86_64-unknown-linux-gnu-$versao.zip"
  base="https://github.com/bitwarden/sdk-sm/releases/download/bws-v$versao"
  curl -fsSL -o "$pasta/$zip" "$base/$zip"
  curl -fsSL -o "$pasta/checksums.txt" "$base/bws-sha256-checksums-$versao.txt"
  (cd "$pasta" && grep " $zip\$" checksums.txt | sha256sum --check --quiet -)
  unzip -q "$pasta/$zip" -d "$pasta"
  BWS="$pasta/bws"
fi
[ -n "${BWS_SERVER_URL:-}" ] || unset BWS_SERVER_URL

"$BWS" secret list --output json > "$pasta/segredos.json"

faltando=()
for chave in $CHAVES; do
  quantas=$(jq --arg k "$chave" 'map(select(.key == $k)) | length' "$pasta/segredos.json")
  if [ "$quantas" != 1 ]; then
    faltando+=("$chave (encontradas: $quantas)")
    continue
  fi
  valor=$(jq -r --arg k "$chave" '.[] | select(.key == $k) | .value' "$pasta/segredos.json")
  while IFS= read -r linha; do
    [ -n "$linha" ] && echo "::add-mask::$linha"
  done <<< "$valor"
  delimitador="FIM_$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
  { echo "$chave<<$delimitador"; echo "$valor"; echo "$delimitador"; } >> "$GITHUB_ENV"
  echo "Lida do Bitwarden: $chave"
done

if [ ${#faltando[@]} -gt 0 ]; then
  echo "::error::Chaves ausentes ou repetidas no Bitwarden: ${faltando[*]}"
  exit 1
fi
