import { prepareIndex, search } from "./search.ts";
import { readStoredFile } from "./storage.ts";
import type { IndexRow, Meta, Person } from "./types.ts";

// The data only changes when the pipeline publishes again; 10 minutes in memory is enough.
const TTL_MS = Number(process.env.PUXA_CACHE_SECONDS ?? 600) * 1000;
const cache = new Map<string, { value: unknown; expires: number }>();

async function readJson<T>(filePath: string): Promise<T | null> {
  const cached = cache.get(filePath);
  if (cached && Date.now() < cached.expires) return cached.value as T;
  const content = await readStoredFile(filePath);
  if (!content) return null; // absence is not cached: the file may be published at any moment
  const value = JSON.parse(content.toString("utf-8")) as T;
  cache.set(filePath, { value, expires: Date.now() + TTL_MS });
  return value;
}

/** Registry IDs are slugs: lowercase letters, digits and hyphens. Anything else is a 404. */
export const isValidId = (id: string) => /^[a-z0-9]+(-[a-z0-9]+)*$/.test(id) && id.length <= 80;

let preparedIndex: { source: IndexRow[]; entries: ReturnType<typeof prepareIndex> } | null = null;

export async function searchPeople(query: string, limit = 20): Promise<IndexRow[]> {
  const index = await readJson<IndexRow[]>("index.json");
  if (!index) throw new Error("index.json not found");
  if (preparedIndex?.source !== index) preparedIndex = { source: index, entries: prepareIndex(index) };
  return search(preparedIndex.entries, query, limit);
}

export const readMeta = () => readJson<Meta>("meta.json");

export async function readPerson(id: string): Promise<Person | null> {
  return isValidId(id) ? readJson<Person>(`people/${id}.json`) : null;
}

export async function readBinary(folder: "photos" | "pdf", id: string, extension: string): Promise<Buffer | null> {
  return isValidId(id) ? readStoredFile(`${folder}/${id}.${extension}`) : null;
}
