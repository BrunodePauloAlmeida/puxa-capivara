import assert from "node:assert/strict";
import { test } from "node:test";

import { buscar, normalizar, prepararIndice } from "./busca.ts";
import type { LinhaIndice } from "./tipos.ts";

const linha = (id: string, nome: string, busca: string): LinhaIndice => ({
  id,
  nome,
  busca,
  cargo: "Deputada federal",
  partido_uf: "X-SP",
  uf: "SP",
  cargos: ["deputado_federal"],
  foto: true,
  iniciais: "XX",
});

const indice = prepararIndice([
  linha("lula", "Lula", "lula luiz inacio da silva"),
  linha("erika-hilton", "Erika Hilton", "erika hilton"),
  linha("benedita-da-silva", "Benedita da Silva", "benedita da silva"),
  linha("marina-silva", "Marina Silva", "marina silva osmarina marina da silva vaz de lima"),
  linha("luiz-lima", "Luiz Lima", "luiz lima"),
]);

const ids = (consulta: string) => buscar(indice, consulta).map((l) => l.id);

test("normaliza acentos, caixa e pontuação", () => {
  assert.equal(normalizar("  Érika   HILTON! "), "erika hilton");
});

test("consulta curta não busca", () => {
  assert.deepEqual(ids("l"), []);
});

test("nome exato, começo do nome, nome de urna, nome civil; empate em ordem alfabética", () => {
  assert.deepEqual(ids("lu"), ["luiz-lima", "lula"]);
  assert.deepEqual(ids("lula"), ["lula"]);
  assert.deepEqual(ids("luiz"), ["luiz-lima", "lula"]);
  assert.deepEqual(ids("silva"), ["benedita-da-silva", "marina-silva", "lula"]);
});

test("nome exato vem antes de quem só começa igual", () => {
  const extra = prepararIndice([linha("lula-da-fonte", "Lula da Fonte", "lula da fonte"), linha("lula", "Lula", "lula")]);
  assert.deepEqual(buscar(extra, "lula").map((l) => l.id), ["lula", "lula-da-fonte"]);
});

test("termos em qualquer ordem, sem acento", () => {
  assert.deepEqual(ids("hilton érika"), ["erika-hilton"]);
  assert.deepEqual(ids("inacio lula"), ["lula"]);
});

test("cada termo precisa casar", () => {
  assert.deepEqual(ids("erika silva"), []);
});
