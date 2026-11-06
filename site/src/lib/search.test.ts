import assert from "node:assert/strict";
import { test } from "node:test";

import { normalize, prepareIndex, search } from "./search.ts";
import type { IndexRow } from "./types.ts";

const row = (id: string, name: string, searchText: string): IndexRow => ({
  id,
  name,
  search: searchText,
  role: "Deputada federal",
  party_state: "X-SP",
  state: "SP",
  roles: ["federal_deputy"],
  photo: true,
  initials: "XX",
});

const index = prepareIndex([
  row("lula", "Lula", "lula luiz inacio da silva"),
  row("erika-hilton", "Erika Hilton", "erika hilton"),
  row("benedita-da-silva", "Benedita da Silva", "benedita da silva"),
  row("marina-silva", "Marina Silva", "marina silva osmarina marina da silva vaz de lima"),
  row("luiz-lima", "Luiz Lima", "luiz lima"),
]);

const ids = (query: string) => search(index, query).map((r) => r.id);

test("normalizes accents, case and punctuation", () => {
  assert.equal(normalize("  Érika   HILTON! "), "erika hilton");
});

test("short query does not search", () => {
  assert.deepEqual(ids("l"), []);
});

test("exact name, name prefix, ballot name, civil name; ties in alphabetical order", () => {
  assert.deepEqual(ids("lu"), ["luiz-lima", "lula"]);
  assert.deepEqual(ids("lula"), ["lula"]);
  assert.deepEqual(ids("luiz"), ["luiz-lima", "lula"]);
  assert.deepEqual(ids("silva"), ["benedita-da-silva", "marina-silva", "lula"]);
});

test("exact name comes before names that only start the same", () => {
  const extra = prepareIndex([row("lula-da-fonte", "Lula da Fonte", "lula da fonte"), row("lula", "Lula", "lula")]);
  assert.deepEqual(search(extra, "lula").map((r) => r.id), ["lula", "lula-da-fonte"]);
});

test("terms in any order, without accents", () => {
  assert.deepEqual(ids("hilton érika"), ["erika-hilton"]);
  assert.deepEqual(ids("inacio lula"), ["lula"]);
});

test("every term must match", () => {
  assert.deepEqual(ids("erika silva"), []);
});
