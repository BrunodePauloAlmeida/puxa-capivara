import type { IndexRow } from "./types.ts";

export const MIN_LENGTH = 2;

/** "Érika  Hilton!" -> "erika hilton" (no accents, lowercase, only letters and digits). */
export function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

interface Entry {
  row: IndexRow;
  name: string;
  nameWords: string[];
  searchWords: string[];
}

export function prepareIndex(index: IndexRow[]): Entry[] {
  return index.map((row) => {
    const name = normalize(row.name);
    return { row, name, nameWords: name.split(" "), searchWords: row.search.split(" ") };
  });
}

const matchesAll = (terms: string[], words: string[]) =>
  terms.every((t) => words.some((w) => w.startsWith(t)));

/**
 * Every query term must be the start of some word of the name (ballot name or civil name).
 * Order: name equal to the query, name starting with it, all terms in the ballot name, all in the civil name;
 * ties broken alphabetically.
 */
export function search(entries: Entry[], query: string, limit = 20): IndexRow[] {
  const q = normalize(query);
  if (q.length < MIN_LENGTH) return [];
  const terms = q.split(" ");
  const matches: { e: Entry; score: number }[] = [];
  for (const e of entries) {
    let score: number;
    if (e.name === q) score = -1;
    else if (e.name.startsWith(q)) score = 0;
    else if (matchesAll(terms, e.nameWords)) score = 1;
    else if (matchesAll(terms, e.searchWords)) score = 2;
    else continue;
    matches.push({ e, score });
  }
  matches.sort((a, b) => a.score - b.score || a.e.name.localeCompare(b.e.name, "pt-BR"));
  return matches.slice(0, limit).map((m) => m.e.row);
}
