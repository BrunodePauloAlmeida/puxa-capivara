#!/usr/bin/env bash
# puxa-capivara infrastructure on Google Cloud: the same as docs/deploy.md does through the console, on the command
# line and with narrower permissions (on the bucket, the repository and the service account, instead of the whole project).
#
# Idempotent: safe to run again; whatever already exists is kept.
# Usage (needs gcloud authenticated as the project owner):
#   PROJECT=puxa-capivara-513419 BUCKET=puxa-capivara-dados infra/gcp-setup.sh
#
# Does not create the Cloud Run service or Firebase: the first deploy creates the service (see docs/deploy.md).
set -euo pipefail

PROJECT=${PROJECT:?set PROJECT to the project ID}
REGION=${REGION:-southamerica-east1}
BUCKET=${BUCKET:-$PROJECT-dados}
REPO_AR=${REPO_AR:-puxa-capivara}
REPO_GITHUB=${REPO_GITHUB:-BrunodePauloAlmeida/puxa-capivara}
POOL=github
PROVIDER=github-actions

g() { gcloud --project "$PROJECT" --quiet "$@"; }
exists() { "$@" >/dev/null 2>&1; }

PROJECT_NUMBER=$(g projects describe "$PROJECT" --format='value(projectNumber)')
SA_SITE=puxa-site@$PROJECT.iam.gserviceaccount.com
SA_DEPLOY=github-deploy@$PROJECT.iam.gserviceaccount.com

echo "== APIs"
g services enable run.googleapis.com artifactregistry.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com storage.googleapis.com cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com

echo "== Artifact Registry: $REPO_AR"
exists g artifacts repositories describe "$REPO_AR" --location "$REGION" ||
  g artifacts repositories create "$REPO_AR" --repository-format docker --location "$REGION"

echo "== Bucket: gs://$BUCKET"
exists g storage buckets describe "gs://$BUCKET" ||
  g storage buckets create "gs://$BUCKET" --location "$REGION" --uniform-bucket-level-access \
    --public-access-prevention

echo "== Service accounts"
# The display names below are the ones the existing service accounts were created with; kept as they are.
exists g iam service-accounts describe "$SA_SITE" ||
  g iam service-accounts create puxa-site --display-name "Site no Cloud Run (lê os dados do bucket)"
exists g iam service-accounts describe "$SA_DEPLOY" ||
  g iam service-accounts create github-deploy --display-name "Deploy pelo GitHub Actions"

echo "== Permissions"
# Site: only reads the data bucket.
g storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:$SA_SITE" --role roles/storage.objectViewer >/dev/null
# Deploy: writes to the bucket and the image repository, publishes Cloud Run revisions using the site's account,
# publishes Firebase Hosting.
g storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:$SA_DEPLOY" --role roles/storage.objectAdmin >/dev/null
g artifacts repositories add-iam-policy-binding "$REPO_AR" --location "$REGION" \
  --member "serviceAccount:$SA_DEPLOY" --role roles/artifactregistry.writer >/dev/null
g iam service-accounts add-iam-policy-binding "$SA_SITE" \
  --member "serviceAccount:$SA_DEPLOY" --role roles/iam.serviceAccountUser >/dev/null
for role in roles/run.developer roles/firebasehosting.admin roles/serviceusage.serviceUsageConsumer; do
  g projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$SA_DEPLOY" --role "$role" --condition None >/dev/null
done

echo "== Workload Identity Federation (keyless GitHub Actions)"
exists g iam workload-identity-pools describe "$POOL" --location global ||
  g iam workload-identity-pools create "$POOL" --location global --display-name GitHub
exists g iam workload-identity-pools providers describe "$PROVIDER" --workload-identity-pool "$POOL" --location global ||
  g iam workload-identity-pools providers create-oidc "$PROVIDER" --workload-identity-pool "$POOL" \
    --location global --display-name "GitHub Actions" \
    --issuer-uri https://token.actions.githubusercontent.com \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition "assertion.repository == '$REPO_GITHUB'"
g iam service-accounts add-iam-policy-binding "$SA_DEPLOY" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository/$REPO_GITHUB" \
  >/dev/null

cat <<EOF

Done. Keys for Bitwarden Secrets Manager (project puxa-capivara; GitHub stores only BITWARDEN_ACCESS_TOKEN):
  GCP_WORKLOAD_IDENTITY_PROVIDER = projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER
  GCP_SA_EMAIL                   = $SA_DEPLOY
The project ($PROJECT) and bucket ($BUCKET) are written into the deploy workflows.
EOF
