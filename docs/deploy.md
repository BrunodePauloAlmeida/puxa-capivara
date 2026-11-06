# Site deploy (v1)

Everything through the browser: the Google Cloud console, the Firebase console and GitHub. No need to install
`gcloud`. It takes about 40 minutes the first time. After that, every merge into `main` publishes the site on
its own.

**Terminal shortcut:** with `gcloud` authenticated as the project owner, `infra/gcp-setup.sh` does steps 1 to 5
(with narrower permissions than the console ones). That is how the `puxa-capivara-513419` project was set up on
November 1, 2026: bucket `puxa-capivara-dados`, site at <https://puxa-capivara-513419.web.app>.

## How it runs

```
browser ──> Firebase Hosting (CDN, HTTPS, domain)
                 │  rewrite of every route
                 v
              Cloud Run: puxa-capivara-site (Next.js, São Paulo)
                 │  reads with the puxa-site service account
                 v
              Cloud Storage: puxa-capivara-dados/web/  (index, JSON profiles, photos, PDFs)
```

- **GitHub Actions** builds the image, pushes it to **Artifact Registry** and deploys it to Cloud Run. It signs
  in to GCP through **Workload Identity Federation**, with no service account key stored anywhere. The federation
  details come from **Bitwarden Secrets Manager**; GitHub only stores the Bitwarden token.
- The data reaches the bucket through the **Publish site data** workflow, which copies the `site-web.tar.gz`
  bundle stored with Git LFS on the `site-data` branch (outside `main`). Later, the pipeline runs as a Cloud Run
  Job and writes straight to the bucket.
- The bucket is private: only Cloud Run reads it. Photos, PDFs and search are served with cache headers, and the
  Firebase CDN caches the responses.

In the steps below, replace **`YOUR_PROJECT`** with the project **ID** (not the name). The ID appears in the
project picker at the top of the console and on the dashboard ("Project ID"). Also write down the **project
number**, which is on the same dashboard.

The console labels below are the English ones. Role names appear in English or Portuguese depending on the
console language, so the role tables list both, plus the role ID, which also works in the search box.

---

## 1. Enable the APIs

Open the link below, replace `YOUR_PROJECT` at the end and click **Enable**:

```
https://console.cloud.google.com/flows/enableapi?apiid=run.googleapis.com,artifactregistry.googleapis.com,iamcredentials.googleapis.com,sts.googleapis.com,storage.googleapis.com,firebase.googleapis.com,firebasehosting.googleapis.com&project=YOUR_PROJECT
```

These are: Cloud Run, Artifact Registry, IAM Service Account Credentials, Security Token Service, Cloud Storage,
Firebase Management and Firebase Hosting.

## 2. Image repository (Artifact Registry)

Console > **Artifact Registry** > **Repositories** > **Create repository**:

| Field | Value |
|---|---|
| Name | `puxa-capivara` |
| Format | Docker |
| Mode | Standard |
| Location type | Region: `southamerica-east1 (São Paulo)` |

Optional, to avoid piling up images: under **Cleanup policies**, keep the 10 most recent versions.

## 3. Data bucket (Cloud Storage)

Console > **Cloud Storage** > **Buckets** > **Create**:

| Field | Value |
|---|---|
| Name | `puxa-capivara-dados` (if you use another one, change `BUCKET` in both deploy workflows) |
| Location type | Region: `southamerica-east1 (São Paulo)` |
| Storage class | Standard |
| Access | Check **Enforce public access prevention**; **Uniform** access control |

Leave the rest at the defaults.

## 4. Two service accounts

Console > **IAM & Admin** > **Service accounts** > **Create service account**. Create both. In the step "Grant
this service account access to project", add the roles in the table.

**`puxa-site`**: what the site uses to read the bucket.

| Role (English / Portuguese console) | ID |
|---|---|
| Storage Object Viewer / Leitor de objetos do Storage | `roles/storage.objectViewer` |

**`github-deploy`**: what GitHub Actions uses to publish.

| Role (English / Portuguese console) | ID |
|---|---|
| Cloud Run Developer / Desenvolvedor do Cloud Run | `roles/run.developer` |
| Artifact Registry Writer / Gravador do Artifact Registry | `roles/artifactregistry.writer` |
| Service Account User / Usuário da conta de serviço | `roles/iam.serviceAccountUser` |
| Storage Object Admin / Administrador de objetos do Storage | `roles/storage.objectAdmin` |
| Firebase Hosting Admin / Administrador do Firebase Hosting | `roles/firebasehosting.admin` |
| Service Usage Consumer / Consumidor do Service Usage | `roles/serviceusage.serviceUsageConsumer` |

The roles apply to the whole project. Since the project only serves puxa-capivara, that is acceptable and much
simpler to set up through the console.

## 5. Let GitHub in without a key (Workload Identity Federation)

Console > **IAM & Admin** > **Workload Identity Federation** > **Create pool**:

1. **Pool**: name `GitHub`, ID `github`. Continue.
2. **Provider**: type **OpenID Connect (OIDC)**.
   - Name `GitHub Actions`, ID `github-actions`
   - Issuer (URL): `https://token.actions.githubusercontent.com`
   - Audiences: **Default audience**
3. **Provider attributes**:

   | Google | OIDC |
   |---|---|
   | `google.subject` | `assertion.sub` |
   | `attribute.repository` | `assertion.repository` |
   | `attribute.repository_owner` | `assertion.repository_owner` |

   Under **Attribute conditions**, add:

   ```
   assertion.repository == 'BrunodePauloAlmeida/puxa-capivara'
   ```

   Save.
4. Back on the pool page, click **Grant access** and choose **Grant access using service account
   impersonation**:
   - Service account: `github-deploy`
   - Principals: attribute `repository`, value `BrunodePauloAlmeida/puxa-capivara`
   - Save. In the "Configure your application" window, just close it (nothing to download).

The full provider name, which goes into Bitwarden in step 8, is:

```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-actions
```

## 6. Cloud Run service (first time, with a sample image)

GitHub Actions replaces the image later. This step exists to get the service created, public and with the right
service account.

Console > **Cloud Run** > **Deploy container** > **Service**:

| Field | Value |
|---|---|
| Container image URL | `us-docker.pkg.dev/cloudrun/container/hello` |
| Service name | `puxa-capivara-site` |
| Region | `southamerica-east1 (São Paulo)` |
| Authentication | **Allow public access** (see the note below) |
| Billing | Request-based |
| Scaling | minimum 0, maximum 3 instances |
| Ingress | All |
| Security (under "Containers, Volumes, Networking, Security") | Service account: `puxa-site` |

Create. If the `...run.app` URL shows the "It's running!" page, it worked.

**Note about the Bloomcore organization:** the organization policy (`iam.allowedPolicyMemberDomains`) only accepts
accounts from the domain, so public access the classic way (`allUsers` as invoker) is refused. There are two ways
out:

- **Disable the invoker IAM check on this service only** (recommended, does not touch the organization policy).
  In the console: Cloud Run > `puxa-capivara-site` > **Security** tab > Authentication > **Allow public access**,
  which in recent consoles does exactly that. In Cloud Shell:

  ```bash
  gcloud run services update puxa-capivara-site --region southamerica-east1 --no-invoker-iam-check
  ```

- Add a policy exception on the project, as was done for Observa Custódia. It allows `allUsers` on any resource in
  the project, so it is broader.

## 7. Firebase Hosting

1. Open <https://console.firebase.google.com> > **Create a project** and choose **Add Firebase to a Google Cloud
   project**. Select `YOUR_PROJECT`.
2. Google Analytics: you can turn it off, it is not used.
3. The plan becomes Blaze automatically, because the project already has billing.
4. In the Firebase menu, open **Hosting** > **Get started** and click through the screens (no need to run the
   commands it shows). This creates the `YOUR_PROJECT.web.app` site.

## 8. Secrets: Bitwarden Secrets Manager, and only the token on GitHub

Secrets live in **Bitwarden Secrets Manager**, the project's official vault. GitHub stores just one thing: the
Bitwarden access token. On every run, the workflows read the secrets by name
(`.github/actions/bitwarden-secrets`), with the official `bws` CLI and a verified checksum, and mask them in the
logs.

In Bitwarden, project **puxa-capivara**, with a **machine account** that has read access to it:

| Key (exact name) | Value |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-actions` |
| `GCP_SA_EMAIL` | `github-deploy@YOUR_PROJECT.iam.gserviceaccount.com` |

On GitHub, under **Settings** > **Secrets and variables** > **Actions** > **New repository secret**:

| Name | Value |
|---|---|
| `BITWARDEN_ACCESS_TOKEN` | the Bitwarden machine account token |

If the Bitwarden organization is on the EU cloud, also create the **variable** `BWS_SERVER_URL` with the value
`https://vault.bitwarden.eu`.

The project ID (`puxa-capivara-513419`) and the bucket name (`puxa-capivara-dados`) are not secret and are written
into the workflows themselves.

## 9. Publish

1. Merge the site PR into `main`. The **Deploy site** workflow runs on its own: image, Cloud Run and Firebase.
2. Under **Actions** > **Publish site data** > **Run workflow**, leave `site-data` and run it. This copies the data
   to the bucket.
3. Open `https://YOUR_PROJECT.web.app`.

If the deploy ran before step 8, run it again by hand: **Actions** > **Deploy site** > **Run workflow**.

On the `puxa-capivara-513419` project, the first publication (data, image, Cloud Run and Firebase) was done from
the terminal on November 1, 2026. From the merge on, GitHub Actions takes over.

## 10. Later (optional)

- **Spending alert**: Console > **Billing** > **Budgets & alerts** > create a monthly budget (for example,
  R$ 50) with alerts at 50%, 90% and 100%.
- **Custom domain**: Firebase > Hosting > **Add custom domain** and create the records it asks for in your DNS.
  The HTTPS certificate is issued automatically.
- **Search engines**: v1 is marked as not indexable (`robots: noindex` in `site/src/app/layout.tsx`), because the
  data is still being validated. To allow indexing, just remove that line.

## Expected cost

With little traffic, it stays within the free tiers or close to them: Cloud Run with a minimum of 0 instances only
charges when there is traffic; the bucket holds about 170 MB; Artifact Registry keeps a few images of about
400 MB. The biggest variable is Firebase Hosting transfer if the site goes viral (each PDF is 180 KB on average).
Hence the spending alert.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `missing the BITWARDEN_ACCESS_TOKEN secret` | Secret not set in the repository (step 8) |
| `Keys missing or duplicated in Bitwarden` | Key name differs from the expected one, key in another project, or the machine account has no access to the project |
| `bws` fails with an authentication error | Token expired or revoked, or an organization on the EU cloud without the `BWS_SERVER_URL` variable |
| `Permission 'iam.serviceAccounts.getAccessToken' denied` in the auth step | Step 5.4 (grant access) missing, or a condition with the wrong repository name |
| `denied: Permission "artifactregistry.repositories.uploadArtifacts"` | The repository is not named `puxa-capivara`, is in another region, or the writer role is missing |
| `Permission 'iam.serviceaccounts.actAs' denied` in Cloud Run | Service Account User missing for `github-deploy` |
| Firebase: `HTTP Error: 403` | Firebase was not added to the project, Hosting was not started (step 7.4), or the Firebase Hosting / Service Usage roles are missing |
| The site opens but shows "Algo deu errado" ("Something went wrong") | Data not published yet (step 9.2), or `puxa-site` lacks Storage Object Viewer |
| The browser shows `Forbidden` | Cloud Run service without public access (step 6 and the note about the organization) |
| The deploy from GitHub complains about `run.services.setIamPolicy` | The invoker IAM check was disabled by another account; run the deploy once as the owner or give `roles/run.admin` to `github-deploy` |

## Updating the data

Today: run the pipeline (`uv run puxa ...` and then `uv run puxa site`), pack `data/site/web` into
`site-web.tar.gz`, replace the file on the `site-data` branch (Git LFS) and run **Publish site data**.

```bash
tar -czf site-web.tar.gz -C data/site/web .
```

Each run downloads about 100 MB from Git LFS, which counts toward the GitHub account's monthly LFS bandwidth
quota.

In Sprint 3 of the roadmap, the pipeline moves to a Cloud Run Job and writes straight to the bucket.
