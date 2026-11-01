import type { LinhaIndice } from "./tipos.ts";

export const MINIMO = 2;

/** "Érika  Hilton!" -> "erika hilton" (sem acento, minúsculas, só letras e números). */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

interface Entrada {
  linha: LinhaIndice;
  nome: string;
  palavrasNome: string[];
  palavrasBusca: string[];
}

export function prepararIndice(indice: LinhaIndice[]): Entrada[] {
  return indice.map((linha) => {
    const nome = normalizar(linha.nome);
    return { linha, nome, palavrasNome: nome.split(" "), palavrasBusca: linha.busca.split(" ") };
  });
}

const casaTodas = (termos: string[], palavras: string[]) =>
  termos.every((t) => palavras.some((p) => p.startsWith(t)));

/**
 * Cada termo da consulta tem que ser começo de alguma palavra do nome (de urna ou civil).
 * Ordem: nome igual à consulta, nome que começa com ela, todos os termos no nome de urna, todos no nome civil;
 * no empate, ordem alfabética.
 */
export function buscar(entradas: Entrada[], consulta: string, limite = 20): LinhaIndice[] {
  const q = normalizar(consulta);
  if (q.length < MINIMO) return [];
  const termos = q.split(" ");
  const achados: { e: Entrada; nota: number }[] = [];
  for (const e of entradas) {
    let nota: number;
    if (e.nome === q) nota = -1;
    else if (e.nome.startsWith(q)) nota = 0;
    else if (casaTodas(termos, e.palavrasNome)) nota = 1;
    else if (casaTodas(termos, e.palavrasBusca)) nota = 2;
    else continue;
    achados.push({ e, nota });
  }
  achados.sort((a, b) => a.nota - b.nota || a.e.nome.localeCompare(b.e.nome, "pt-BR"));
  return achados.slice(0, limite).map((a) => a.e.linha);
}
