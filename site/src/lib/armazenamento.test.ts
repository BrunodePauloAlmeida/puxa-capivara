import assert from "node:assert/strict";
import { test } from "node:test";

// Caminho de produção: bucket do Cloud Storage com o token do servidor de metadados do Cloud Run.
process.env.PUXA_BUCKET = "bucket-teste";
process.env.PUXA_PREFIXO = "web/";

test("lê do Cloud Storage com o token do Cloud Run e guarda o token", async () => {
  const chamadas: { url: string; headers: Record<string, string> }[] = [];
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    chamadas.push({ url, headers: (init?.headers ?? {}) as Record<string, string> });
    if (url.includes("metadata.google.internal")) {
      return Response.json({ access_token: "tok", expires_in: 3600 });
    }
    if (url.includes("nao-existe")) return new Response("", { status: 404 });
    return new Response("conteúdo");
  }) as typeof fetch;

  const { lerArquivo } = await import("./armazenamento.ts");
  assert.equal((await lerArquivo("pessoas/lula.json"))?.toString(), "conteúdo");
  assert.equal(await lerArquivo("pessoas/nao-existe.json"), null);

  const token = chamadas.filter((c) => c.url.includes("metadata"));
  assert.equal(token.length, 1, "o token é reaproveitado até expirar");
  assert.equal(token[0].headers["Metadata-Flavor"], "Google");
  const leitura = chamadas.find((c) => c.url.includes("storage.googleapis.com"));
  assert.equal(
    leitura?.url,
    "https://storage.googleapis.com/storage/v1/b/bucket-teste/o/web%2Fpessoas%2Flula.json?alt=media",
  );
  assert.equal(leitura?.headers.Authorization, "Bearer tok");
});
