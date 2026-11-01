# Deploy do site (v1)

Tudo pelo navegador: console do Google Cloud, console do Firebase e GitHub. Não precisa instalar `gcloud`.
Leva uns 40 minutos na primeira vez. Depois disso, cada merge na `main` publica o site sozinho.

**Atalho pelo terminal:** com `gcloud` autenticado como dono do projeto, `infra/gcp-setup.sh` faz os passos 1 a 5
(com permissões mais estreitas que as do console). Foi assim que o projeto `puxa-capivara-513419` foi montado
em 01/11/2026: bucket `puxa-capivara-dados`, site em <https://puxa-capivara-513419.web.app>.

## Como fica no ar

```
navegador ──> Firebase Hosting (CDN, HTTPS, domínio)
                 │  rewrite de todas as rotas
                 v
              Cloud Run: puxa-capivara-site (Next.js, São Paulo)
                 │  lê com a conta de serviço puxa-site
                 v
              Cloud Storage: puxa-capivara-dados/web/  (índice, fichas em JSON, fotos, PDFs)
```

- **GitHub Actions** constrói a imagem, envia para o **Artifact Registry** e publica no Cloud Run. Ele entra no
  GCP pela **Workload Identity Federation**, sem chave de conta de serviço guardada em lugar nenhum. Os dados da
  federação vêm do **Bitwarden Secrets Manager**; o GitHub só guarda o token do Bitwarden.
- Os dados chegam ao bucket pelo workflow **Publicar dados do site**, que copia o pacote `site-web.tar.gz` guardado
  com Git LFS no branch `dados-site` (fora da `main`). Mais tarde, o pipeline roda como Cloud Run Job e grava
  direto no bucket.
- O bucket é privado: só o Cloud Run lê. Fotos, PDFs e a busca saem com cabeçalho de cache, e a CDN do Firebase
  guarda as respostas.

Nos passos abaixo, troque **`SEU_PROJETO`** pelo **ID** do projeto (não o nome). O ID aparece no seletor de
projetos, no topo do console, e no painel inicial ("ID do projeto"). Anote também o **número do projeto**, que
fica no mesmo painel.

Os nomes dos papéis aparecem em inglês ou em português, conforme o idioma do console. Por isso a lista traz os
dois, mais o ID do papel, que também funciona na busca.

---

## 1. Ativar as APIs

Abra o link abaixo, troque `SEU_PROJETO` no fim e clique em **Ativar**:

```
https://console.cloud.google.com/flows/enableapi?apiid=run.googleapis.com,artifactregistry.googleapis.com,iamcredentials.googleapis.com,sts.googleapis.com,storage.googleapis.com,firebase.googleapis.com,firebasehosting.googleapis.com&project=SEU_PROJETO
```

São estas: Cloud Run, Artifact Registry, IAM Service Account Credentials, Security Token Service, Cloud Storage,
Firebase Management e Firebase Hosting.

## 2. Repositório de imagens (Artifact Registry)

Console > **Artifact Registry** > **Repositórios** > **Criar repositório**:

| Campo | Valor |
|---|---|
| Nome | `puxa-capivara` |
| Formato | Docker |
| Modo | Padrão |
| Tipo de local | Região: `southamerica-east1 (São Paulo)` |

Opcional, para não acumular imagens: em **Política de limpeza**, mantenha as 10 versões mais recentes.

## 3. Bucket dos dados (Cloud Storage)

Console > **Cloud Storage** > **Buckets** > **Criar**:

| Campo | Valor |
|---|---|
| Nome | `puxa-capivara-dados` (se usar outro, troque `BUCKET` nos dois workflows de deploy) |
| Tipo de local | Região: `southamerica-east1 (São Paulo)` |
| Classe | Standard |
| Acesso | Marque **Aplicar a prevenção do acesso público**; controle de acesso **Uniforme** |

O resto fica no padrão.

## 4. Duas contas de serviço

Console > **IAM e administrador** > **Contas de serviço** > **Criar conta de serviço**. Crie as duas. No passo
"Conceder acesso a esta conta de serviço ao projeto", adicione os papéis da tabela.

**`puxa-site`**: quem o site usa para ler o bucket.

| Papel | ID |
|---|---|
| Storage Object Viewer / Leitor de objetos do Storage | `roles/storage.objectViewer` |

**`github-deploy`**: quem o GitHub Actions usa para publicar.

| Papel | ID |
|---|---|
| Cloud Run Developer / Desenvolvedor do Cloud Run | `roles/run.developer` |
| Artifact Registry Writer / Gravador do Artifact Registry | `roles/artifactregistry.writer` |
| Service Account User / Usuário da conta de serviço | `roles/iam.serviceAccountUser` |
| Storage Object Admin / Administrador de objetos do Storage | `roles/storage.objectAdmin` |
| Firebase Hosting Admin / Administrador do Firebase Hosting | `roles/firebasehosting.admin` |
| Service Usage Consumer / Consumidor do Service Usage | `roles/serviceusage.serviceUsageConsumer` |

Os papéis valem para o projeto inteiro. Como o projeto só serve ao puxa-capivara, isso é aceitável e bem mais
simples de configurar pelo console.

## 5. Deixar o GitHub entrar sem chave (Workload Identity Federation)

Console > **IAM e administrador** > **Federação de identidade da carga de trabalho** > **Criar pool**:

1. **Pool**: nome `GitHub`, ID `github`. Continuar.
2. **Provedor**: tipo **OpenID Connect (OIDC)**.
   - Nome `GitHub Actions`, ID `github-actions`
   - Emissor (URL): `https://token.actions.githubusercontent.com`
   - Públicos: **Público padrão**
3. **Atributos do provedor**:

   | Google | OIDC |
   |---|---|
   | `google.subject` | `assertion.sub` |
   | `attribute.repository` | `assertion.repository` |
   | `attribute.repository_owner` | `assertion.repository_owner` |

   Em **Condições de atributo**, adicione:

   ```
   assertion.repository == 'BrunodePauloAlmeida/puxa-capivara'
   ```

   Salvar.
4. De volta à página do pool, clique em **Conceder acesso** e escolha **Conceder acesso usando a representação da
   conta de serviço**:
   - Conta de serviço: `github-deploy`
   - Principais: atributo `repository`, valor `BrunodePauloAlmeida/puxa-capivara`
   - Salvar. Na janela "Configurar seu aplicativo", só feche (não precisa baixar nada).

O nome completo do provedor, que vai para o GitHub no passo 8, é:

```
projects/NUMERO_DO_PROJETO/locations/global/workloadIdentityPools/github/providers/github-actions
```

## 6. Serviço do Cloud Run (primeira vez, com imagem de exemplo)

O GitHub Actions troca a imagem depois. Este passo existe para deixar o serviço criado, público e com a conta
de serviço certa.

Console > **Cloud Run** > **Implantar contêiner** > **Serviço**:

| Campo | Valor |
|---|---|
| Imagem | `us-docker.pkg.dev/cloudrun/container/hello` |
| Nome do serviço | `puxa-capivara-site` |
| Região | `southamerica-east1 (São Paulo)` |
| Autenticação | **Permitir acesso público** (veja a nota abaixo) |
| Faturamento | Baseado em solicitações |
| Escalonamento | mínimo 0, máximo 3 instâncias |
| Entrada | Todas |
| Segurança (em "Contêineres, volumes, rede, segurança") | Conta de serviço: `puxa-site` |

Criar. Se a URL `...run.app` mostrar a página "It's running!", deu certo.

**Nota sobre a organização Bloomcore:** a política da organização (`iam.allowedPolicyMemberDomains`) só aceita
contas do domínio, então o acesso público pela forma clássica (`allUsers` como invocador) é recusado. Há duas
saídas:

- **Desativar a verificação de IAM do invocador só neste serviço** (recomendado, não mexe na política da
  organização). No console: Cloud Run > `puxa-capivara-site` > aba **Segurança** > Autenticação > **Permitir acesso
  público**, que nos consoles recentes faz exatamente isso. No Cloud Shell:

  ```bash
  gcloud run services update puxa-capivara-site --region southamerica-east1 --no-invoker-iam-check
  ```

- Abrir uma exceção à política no projeto, como foi feito no Observa Custódia. Libera `allUsers` para qualquer
  recurso do projeto, então é mais amplo.

## 7. Firebase Hosting

1. Abra <https://console.firebase.google.com> > **Criar um projeto** e escolha **Adicionar o Firebase a um projeto do
   Google Cloud** (ou "Add Firebase to a Google Cloud project"). Selecione `SEU_PROJETO`.
2. Google Analytics: pode desativar, não é usado.
3. O plano fica Blaze automaticamente, porque o projeto já tem faturamento.
4. No menu do Firebase, abra **Hosting** > **Vamos começar** e avance pelas telas (não precisa rodar os comandos
   que ele mostra). Isso cria o site `SEU_PROJETO.web.app`.

## 8. Segredos: Bitwarden Secrets Manager, e só o token no GitHub

Os segredos ficam no **Bitwarden Secrets Manager**, que é o cofre oficial do projeto. O GitHub guarda uma coisa só: o
token de acesso ao Bitwarden. A cada execução, os workflows leem os segredos pelo nome
(`.github/actions/segredos-bitwarden`), com a CLI oficial `bws` e checksum conferido, e os mascaram nos logs.

No Bitwarden, projeto **puxa-capivara**, com uma **conta de máquina** que tenha leitura nele:

| Chave (nome exato) | Valor |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/NUMERO_DO_PROJETO/locations/global/workloadIdentityPools/github/providers/github-actions` |
| `GCP_SA_EMAIL` | `github-deploy@SEU_PROJETO.iam.gserviceaccount.com` |

No GitHub, em **Settings** > **Secrets and variables** > **Actions** > **New repository secret**:

| Nome | Valor |
|---|---|
| `BITWARDEN_ACCESS_TOKEN` | token da conta de máquina do Bitwarden |

Se a organização no Bitwarden estiver na nuvem europeia, crie também a **variável** `BWS_SERVER_URL` com o valor
`https://vault.bitwarden.eu`.

O ID do projeto (`puxa-capivara-513419`) e o nome do bucket (`puxa-capivara-dados`) não são segredo e ficam
escritos nos próprios workflows.

## 9. Publicar

1. Faça o merge do PR do site na `main`. O workflow **Deploy do site** roda sozinho: imagem, Cloud Run e Firebase.
2. Em **Actions** > **Publicar dados do site** > **Run workflow**, deixe `dados-site` e rode. Isso copia os
   dados para o bucket.
3. Abra `https://SEU_PROJETO.web.app`.

Se o deploy rodou antes do passo 8, rode de novo à mão: **Actions** > **Deploy do site** > **Run workflow**.

No projeto `puxa-capivara-513419`, a primeira publicação (dados, imagem, Cloud Run e Firebase) foi feita pelo
terminal em 01/11/2026. A partir do merge, o GitHub Actions assume.

## 10. Depois (opcional)

- **Alerta de gasto**: Console > **Faturamento** > **Orçamentos e alertas** > criar um orçamento mensal (por
  exemplo, R$ 50) com alertas em 50%, 90% e 100%.
- **Domínio próprio**: Firebase > Hosting > **Adicionar domínio personalizado** e criar no seu DNS os registros que
  ele pedir. O certificado HTTPS sai sozinho.
- **Buscadores**: a v1 está marcada para não ser indexada (`robots: noindex` em `site/src/app/layout.tsx`),
  porque os dados ainda estão em validação. Para liberar, é só remover essa linha.

## Custo esperado

Com pouco tráfego, fica dentro das faixas gratuitas ou perto delas: Cloud Run com mínimo de 0 instâncias só cobra
quando há acesso; o bucket tem uns 170 MB; o Artifact Registry guarda poucas imagens de uns 400 MB. A maior
variável é a transferência do Firebase Hosting se o site viralizar (cada PDF tem em média 180 KB). Por isso o
alerta de gasto.

## Se der erro

| Sintoma | Causa provável |
|---|---|
| `falta o secret BITWARDEN_ACCESS_TOKEN` | Secret não cadastrado no repositório (passo 8) |
| `Chaves ausentes ou repetidas no Bitwarden` | Nome da chave diferente do esperado, chave em outro projeto, ou conta de máquina sem acesso ao projeto |
| `bws` falha com erro de autenticação | Token vencido ou revogado, ou organização na nuvem europeia sem a variável `BWS_SERVER_URL` |
| `Permission 'iam.serviceAccounts.getAccessToken' denied` no passo de autenticação | Passo 5.4 (conceder acesso) faltando, ou condição com o nome do repositório errado |
| `denied: Permission "artifactregistry.repositories.uploadArtifacts"` | Repositório não se chama `puxa-capivara`, está em outra região, ou falta o papel de gravador |
| `Permission 'iam.serviceaccounts.actAs' denied` no Cloud Run | Falta Service Account User para `github-deploy` |
| Firebase: `HTTP Error: 403` | Firebase não foi adicionado ao projeto, Hosting não foi iniciado (passo 7.4), ou faltam os papéis do Firebase Hosting / Service Usage |
| Site abre, mas mostra "Algo deu errado" | Dados ainda não publicados (passo 9.2), ou `puxa-site` sem Leitor de objetos do Storage |
| Navegador mostra `Forbidden` | Serviço do Cloud Run sem acesso público (passo 6 e a nota sobre a organização) |
| Deploy pelo GitHub reclama de `run.services.setIamPolicy` | A verificação de IAM do invocador foi desativada por outra conta; rode o deploy uma vez como dono ou dê `roles/run.admin` à `github-deploy` |

## Atualizar os dados

Hoje: rodar o pipeline (`uv run puxa ...` e depois `uv run puxa site`), empacotar `dados/site/web` em
`site-web.tar.gz`, substituir o arquivo no branch `dados-site` (Git LFS) e rodar **Publicar dados do site**.

```bash
tar -czf site-web.tar.gz -C dados/site/web .
```

Cada execução baixa uns 100 MB do Git LFS, o que conta na cota mensal de transferência LFS da conta do GitHub.

Na Sprint 3 do roadmap, o pipeline passa a rodar no Cloud Run Job e grava direto no bucket.
