#!/usr/bin/env bash
# Reads keys from Bitwarden Secrets Manager (by name) and exports them, masked, to the following steps of the job.
# Environment: BWS_ACCESS_TOKEN, KEYS (names separated by spaces or newlines), BWS_SERVER_URL (optional) and
# BWS (optional, path to an already installed bws; without it, downloads the official CLI and verifies the checksum).
set -euo pipefail

: "${BWS_ACCESS_TOKEN:?missing the BITWARDEN_ACCESS_TOKEN secret in the repository (Settings > Secrets and variables > Actions)}"
: "${KEYS:?no keys requested}"
: "${GITHUB_ENV:?must run inside GitHub Actions}"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

if [ -z "${BWS:-}" ]; then
  version=2.1.0
  zip="bws-x86_64-unknown-linux-gnu-$version.zip"
  base="https://github.com/bitwarden/sdk-sm/releases/download/bws-v$version"
  curl -fsSL -o "$tmpdir/$zip" "$base/$zip"
  curl -fsSL -o "$tmpdir/checksums.txt" "$base/bws-sha256-checksums-$version.txt"
  (cd "$tmpdir" && grep " $zip\$" checksums.txt | sha256sum --check --quiet -)
  unzip -q "$tmpdir/$zip" -d "$tmpdir"
  BWS="$tmpdir/bws"
fi
[ -n "${BWS_SERVER_URL:-}" ] || unset BWS_SERVER_URL

"$BWS" secret list --output json > "$tmpdir/secrets.json"

missing=()
for key in $KEYS; do
  count=$(jq --arg k "$key" 'map(select(.key == $k)) | length' "$tmpdir/secrets.json")
  if [ "$count" != 1 ]; then
    missing+=("$key (found: $count)")
    continue
  fi
  value=$(jq -r --arg k "$key" '.[] | select(.key == $k) | .value' "$tmpdir/secrets.json")
  while IFS= read -r line; do
    [ -n "$line" ] && echo "::add-mask::$line"
  done <<< "$value"
  delimiter="EOF_$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
  { echo "$key<<$delimiter"; echo "$value"; echo "$delimiter"; } >> "$GITHUB_ENV"
  echo "Read from Bitwarden: $key"
done

if [ ${#missing[@]} -gt 0 ]; then
  echo "::error::Keys missing or duplicated in Bitwarden: ${missing[*]}"
  exit 1
fi
