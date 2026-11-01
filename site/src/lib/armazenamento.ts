/**
 * De onde vêm os dados do site.
 *
 * - Produção (Cloud Run): bucket do Cloud Storage em PUXA_BUCKET, pasta PUXA_PREFIXO (padrão "web"). A conta de
 *   serviço do Cloud Run lê com o token do servidor de metadados; o bucket não precisa ser público.
 * - Desenvolvimento: pasta local PUXA_DADOS_DIR (padrão ../dados/site/web, saída de `uv run puxa site`).
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

const BUCKET = process.env.PUXA_BUCKET;
const PREFIXO = (process.env.PUXA_PREFIXO ?? "web").replace(/\/+$/, "");
const PASTA = process.env.PUXA_DADOS_DIR ?? path.resolve(/*turbopackIgnore: true*/ process.cwd(), "../dados/site/web");
const METADADOS = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token";

let token: { valor: string; expira: number } | null = null;

async function tokenDeAcesso(): Promise<string> {
  if (token && Date.now() < token.expira) return token.valor;
  const r = await fetch(METADADOS, { headers: { "Metadata-Flavor": "Google" }, cache: "no-store" });
  if (!r.ok) throw new Error(`Servidor de metadados respondeu ${r.status}`);
  const { access_token, expires_in } = (await r.json()) as { access_token: string; expires_in: number };
  token = { valor: access_token, expira: Date.now() + (expires_in - 60) * 1000 };
  return access_token;
}

/** Conteúdo do arquivo, ou null se ele não existe. */
export async function lerArquivo(caminho: string): Promise<Buffer | null> {
  if (!BUCKET) {
    try {
      return await readFile(path.join(/*turbopackIgnore: true*/ PASTA, caminho));
    } catch (erro) {
      if ((erro as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw erro;
    }
  }
  const objeto = encodeURIComponent(`${PREFIXO}/${caminho}`);
  const url = `https://storage.googleapis.com/storage/v1/b/${BUCKET}/o/${objeto}?alt=media`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${await tokenDeAcesso()}` }, cache: "no-store" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Cloud Storage respondeu ${r.status} para ${caminho}`);
  return Buffer.from(await r.arrayBuffer());
}
