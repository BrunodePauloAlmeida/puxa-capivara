import { lerArquivo } from "./armazenamento.ts";
import { buscar, prepararIndice } from "./busca.ts";
import type { LinhaIndice, Meta, Pessoa } from "./tipos.ts";

// Os dados mudam só quando o pipeline publica de novo; 10 minutos em memória bastam.
const VALIDADE_MS = Number(process.env.PUXA_CACHE_SEGUNDOS ?? 600) * 1000;
const cache = new Map<string, { valor: unknown; expira: number }>();

async function lerJson<T>(caminho: string): Promise<T | null> {
  const guardado = cache.get(caminho);
  if (guardado && Date.now() < guardado.expira) return guardado.valor as T;
  const conteudo = await lerArquivo(caminho);
  if (!conteudo) return null; // não guarda a ausência: o arquivo pode ser publicado a qualquer momento
  const valor = JSON.parse(conteudo.toString("utf-8")) as T;
  cache.set(caminho, { valor, expira: Date.now() + VALIDADE_MS });
  return valor;
}

/** IDs do cadastro são slugs: letras minúsculas, números e hífen. Qualquer outra coisa é 404. */
export const idValido = (id: string) => /^[a-z0-9]+(-[a-z0-9]+)*$/.test(id) && id.length <= 80;

let indicePreparado: { fonte: LinhaIndice[]; entradas: ReturnType<typeof prepararIndice> } | null = null;

export async function pesquisar(consulta: string, limite = 20): Promise<LinhaIndice[]> {
  const indice = await lerJson<LinhaIndice[]>("indice.json");
  if (!indice) throw new Error("indice.json não encontrado");
  if (indicePreparado?.fonte !== indice) indicePreparado = { fonte: indice, entradas: prepararIndice(indice) };
  return buscar(indicePreparado.entradas, consulta, limite);
}

export const lerMeta = () => lerJson<Meta>("meta.json");

export async function lerPessoa(id: string): Promise<Pessoa | null> {
  return idValido(id) ? lerJson<Pessoa>(`pessoas/${id}.json`) : null;
}

export async function lerBinario(pasta: "fotos" | "pdf", id: string, extensao: string): Promise<Buffer | null> {
  return idValido(id) ? lerArquivo(`${pasta}/${id}.${extensao}`) : null;
}
