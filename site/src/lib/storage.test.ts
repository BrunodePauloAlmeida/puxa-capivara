import assert from "node:assert/strict";
import { test } from "node:test";

// Production path: Cloud Storage bucket with the token from the Cloud Run metadata server.
process.env.PUXA_BUCKET = "test-bucket";
process.env.PUXA_PREFIX = "web/";

test("reads from Cloud Storage with the Cloud Run token and caches the token", async () => {
  const calls: { url: string; headers: Record<string, string> }[] = [];
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ url, headers: (init?.headers ?? {}) as Record<string, string> });
    if (url.includes("metadata.google.internal")) {
      return Response.json({ access_token: "tok", expires_in: 3600 });
    }
    if (url.includes("does-not-exist")) return new Response("", { status: 404 });
    return new Response("content");
  }) as typeof fetch;

  const { readStoredFile } = await import("./storage.ts");
  assert.equal((await readStoredFile("people/lula.json"))?.toString(), "content");
  assert.equal(await readStoredFile("people/does-not-exist.json"), null);

  const token = calls.filter((c) => c.url.includes("metadata"));
  assert.equal(token.length, 1, "the token is reused until it expires");
  assert.equal(token[0].headers["Metadata-Flavor"], "Google");
  const read = calls.find((c) => c.url.includes("storage.googleapis.com"));
  assert.equal(
    read?.url,
    "https://storage.googleapis.com/storage/v1/b/test-bucket/o/web%2Fpeople%2Flula.json?alt=media",
  );
  assert.equal(read?.headers.Authorization, "Bearer tok");
});
