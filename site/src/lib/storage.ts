/**
 * Where the site data comes from.
 *
 * - Production (Cloud Run): Cloud Storage bucket in PUXA_BUCKET, folder PUXA_PREFIX (default "web"). The Cloud Run
 *   service account reads with the token from the metadata server; the bucket does not need to be public.
 * - Development: local folder PUXA_DATA_DIR (default ../data/site/web, output of `uv run puxa site`).
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

const BUCKET = process.env.PUXA_BUCKET;
const PREFIX = (process.env.PUXA_PREFIX ?? "web").replace(/\/+$/, "");
const FOLDER = process.env.PUXA_DATA_DIR ?? path.resolve(/*turbopackIgnore: true*/ process.cwd(), "../data/site/web");
const METADATA = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token";

let token: { value: string; expires: number } | null = null;

async function accessToken(): Promise<string> {
  if (token && Date.now() < token.expires) return token.value;
  const r = await fetch(METADATA, { headers: { "Metadata-Flavor": "Google" }, cache: "no-store" });
  if (!r.ok) throw new Error(`Metadata server responded ${r.status}`);
  const { access_token, expires_in } = (await r.json()) as { access_token: string; expires_in: number };
  token = { value: access_token, expires: Date.now() + (expires_in - 60) * 1000 };
  return access_token;
}

/** File contents, or null if the file does not exist. */
export async function readStoredFile(filePath: string): Promise<Buffer | null> {
  if (!BUCKET) {
    try {
      return await readFile(path.join(/*turbopackIgnore: true*/ FOLDER, filePath));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw error;
    }
  }
  const object = encodeURIComponent(`${PREFIX}/${filePath}`);
  const url = `https://storage.googleapis.com/storage/v1/b/${BUCKET}/o/${object}?alt=media`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${await accessToken()}` }, cache: "no-store" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Cloud Storage responded ${r.status} for ${filePath}`);
  return Buffer.from(await r.arrayBuffer());
}
