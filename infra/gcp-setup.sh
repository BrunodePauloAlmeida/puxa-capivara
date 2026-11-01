#!/usr/bin/env bash
# Infraestrutura do puxa-capivara no Google Cloud: o mesmo que docs/deploy.md faz pelo console, em linha de comando
# e com permissões mais estreitas (no bucket, no repositório e na conta de serviço, em vez do projeto todo).
#
# Idempotente: pode rodar de novo; o que já existe é mantido.
# Uso (precisa de gcloud autenticado como dono do projeto):
#   PROJETO=puxa-capivara-513419 BUCKET=puxa-capivara-dados infra/gcp-setup.sh
#
# Não cria o serviço do Cloud Run nem o Firebase: o primeiro deploy cria o serviço (ver docs/deploy.md).
set -euo pipefail

PROJETO=${PROJETO:?defina PROJETO com o ID do projeto}
REGIAO=${REGIAO:-southamerica-east1}
BUCKET=${BUCKET:-$PROJETO-dados}
REPO_AR=${REPO_AR:-puxa-capivara}
REPO_GITHUB=${REPO_GITHUB:-BrunodePauloAlmeida/puxa-capivara}
POOL=github
PROVEDOR=github-actions

g() { gcloud --project "$PROJETO" --quiet "$@"; }
existe() { "$@" >/dev/null 2>&1; }

NUMERO=$(g projects describe "$PROJETO" --format='value(projectNumber)')
SA_SITE=puxa-site@$PROJETO.iam.gserviceaccount.com
SA_DEPLOY=github-deploy@$PROJETO.iam.gserviceaccount.com

echo "== APIs"
g services enable run.googleapis.com artifactregistry.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com storage.googleapis.com cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com

echo "== Artifact Registry: $REPO_AR"
existe g artifacts repositories describe "$REPO_AR" --location "$REGIAO" ||
  g artifacts repositories create "$REPO_AR" --repository-format docker --location "$REGIAO"

echo "== Bucket: gs://$BUCKET"
existe g storage buckets describe "gs://$BUCKET" ||
  g storage buckets create "gs://$BUCKET" --location "$REGIAO" --uniform-bucket-level-access \
    --public-access-prevention

echo "== Contas de serviço"
existe g iam service-accounts describe "$SA_SITE" ||
  g iam service-accounts create puxa-site --display-name "Site no Cloud Run (lê os dados do bucket)"
existe g iam service-accounts describe "$SA_DEPLOY" ||
  g iam service-accounts create github-deploy --display-name "Deploy pelo GitHub Actions"

echo "== Permissões"
# Site: só lê o bucket dos dados.
g storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:$SA_SITE" --role roles/storage.objectViewer >/dev/null
# Deploy: grava no bucket e no repositório de imagens, publica revisões do Cloud Run usando a conta do site,
# publica o Firebase Hosting.
g storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:$SA_DEPLOY" --role roles/storage.objectAdmin >/dev/null
g artifacts repositories add-iam-policy-binding "$REPO_AR" --location "$REGIAO" \
  --member "serviceAccount:$SA_DEPLOY" --role roles/artifactregistry.writer >/dev/null
g iam service-accounts add-iam-policy-binding "$SA_SITE" \
  --member "serviceAccount:$SA_DEPLOY" --role roles/iam.serviceAccountUser >/dev/null
for papel in roles/run.developer roles/firebasehosting.admin roles/serviceusage.serviceUsageConsumer; do
  g projects add-iam-policy-binding "$PROJETO" \
    --member "serviceAccount:$SA_DEPLOY" --role "$papel" --condition None >/dev/null
done

echo "== Workload Identity Federation (GitHub Actions sem chave)"
existe g iam workload-identity-pools describe "$POOL" --location global ||
  g iam workload-identity-pools create "$POOL" --location global --display-name GitHub
existe g iam workload-identity-pools providers describe "$PROVEDOR" --workload-identity-pool "$POOL" --location global ||
  g iam workload-identity-pools providers create-oidc "$PROVEDOR" --workload-identity-pool "$POOL" \
    --location global --display-name "GitHub Actions" \
    --issuer-uri https://token.actions.githubusercontent.com \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition "assertion.repository == '$REPO_GITHUB'"
g iam service-accounts add-iam-policy-binding "$SA_DEPLOY" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$NUMERO/locations/global/workloadIdentityPools/$POOL/attribute.repository/$REPO_GITHUB" \
  >/dev/null

cat <<FIM

Pronto. Chaves para o Bitwarden Secrets Manager (projeto puxa-capivara; o GitHub guarda só o BITWARDEN_ACCESS_TOKEN):
  GCP_WORKLOAD_IDENTITY_PROVIDER = projects/$NUMERO/locations/global/workloadIdentityPools/$POOL/providers/$PROVEDOR
  GCP_SA_EMAIL                   = $SA_DEPLOY
Projeto ($PROJETO) e bucket ($BUCKET) ficam escritos nos workflows de deploy.
FIM
