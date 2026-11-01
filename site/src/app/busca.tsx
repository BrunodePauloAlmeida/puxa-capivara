"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { LinhaIndice } from "@/lib/tipos.ts";

const MINIMO = 2;

export function Miniatura({ pessoa }: { pessoa: Pick<LinhaIndice, "id" | "foto" | "iniciais"> }) {
  return pessoa.foto ? (
    // As fotos já saem reduzidas do pipeline; next/image não traria ganho aqui.
    <img className="miniatura" src={`/foto/${pessoa.id}`} alt="" width={42} height={56} loading="lazy" />
  ) : (
    <span className="miniatura" aria-hidden="true">
      {pessoa.iniciais}
    </span>
  );
}

export function Busca({ consultaInicial, iniciais }: { consultaInicial: string; iniciais: LinhaIndice[] }) {
  const router = useRouter();
  const [consulta, setConsulta] = useState(consultaInicial);
  const [resultados, setResultados] = useState(iniciais);
  const [buscado, setBuscado] = useState(consultaInicial.trim().length >= MINIMO ? consultaInicial.trim() : "");
  const [erro, setErro] = useState(false);
  const lista = useRef<HTMLUListElement>(null);
  const campo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const q = consulta.trim();
    if (q === buscado) return;
    if (q.length < MINIMO) {
      setResultados([]);
      setBuscado("");
      window.history.replaceState(null, "", "/");
      return;
    }
    const controle = new AbortController();
    const espera = setTimeout(async () => {
      try {
        const r = await fetch(`/api/busca?q=${encodeURIComponent(q)}`, { signal: controle.signal });
        if (!r.ok) throw new Error(String(r.status));
        const dados = (await r.json()) as { resultados: LinhaIndice[] };
        setResultados(dados.resultados);
        setBuscado(q);
        setErro(false);
        window.history.replaceState(null, "", `/?q=${encodeURIComponent(q)}`);
      } catch (e) {
        if ((e as Error).name !== "AbortError") setErro(true);
      }
    }, 150);
    return () => {
      clearTimeout(espera);
      controle.abort();
    };
  }, [consulta, buscado]);

  const links = () => Array.from(lista.current?.querySelectorAll("a") ?? []);

  function teclaNoCampo(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" && resultados.length) {
      e.preventDefault();
      links()[0]?.focus();
    } else if (e.key === "Escape") {
      setConsulta("");
    }
  }

  function teclaNaLista(e: React.KeyboardEvent<HTMLUListElement>) {
    const todos = links();
    const atual = todos.indexOf(document.activeElement as HTMLAnchorElement);
    if (e.key === "ArrowDown" && atual < todos.length - 1) {
      e.preventDefault();
      todos[atual + 1].focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (atual <= 0) campo.current?.focus();
      else todos[atual - 1].focus();
    }
  }

  const q = consulta.trim();
  let status = "";
  if (erro) status = "Não foi possível buscar agora. Tente de novo em instantes.";
  else if (q.length > 0 && q.length < MINIMO) status = "Digite pelo menos duas letras.";
  else if (buscado && q === buscado)
    status =
      resultados.length === 0
        ? `Nenhum nome encontrado para "${buscado}".`
        : resultados.length === 1
          ? "1 resultado"
          : `${resultados.length} resultados${resultados.length === 20 ? " (os 20 mais próximos)" : ""}`;

  return (
    <div className="busca">
      <form
        role="search"
        action="/"
        onSubmit={(e) => {
          e.preventDefault();
          if (resultados[0] && q === buscado) router.push(`/ficha/${resultados[0].id}`);
        }}
      >
        <label htmlFor="q">Nome do político</label>
        <div className="campo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            ref={campo}
            id="q"
            name="q"
            type="search"
            value={consulta}
            onChange={(e) => setConsulta(e.target.value)}
            onKeyDown={teclaNoCampo}
            placeholder="Ex.: Erika Hilton, Tarcísio, Davi Alcolumbre"
            autoComplete="off"
            autoCapitalize="words"
            spellCheck={false}
            enterKeyHint="search"
            aria-describedby="status-busca"
            autoFocus={!consultaInicial}
          />
        </div>
      </form>
      <p id="status-busca" className="status" aria-live="polite">
        {status}
      </p>
      {resultados.length > 0 && (
        <ul className="resultados" ref={lista} onKeyDown={teclaNaLista} aria-label="Resultados da busca">
          {resultados.map((p) => (
            <li key={p.id}>
              <Link className="resultado" href={`/ficha/${p.id}`} prefetch={false}>
                <Miniatura pessoa={p} />
                <span>
                  <strong>{p.nome}</strong>
                  <span className="cargo">{[p.cargo, p.partido_uf].filter(Boolean).join(" · ")}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
