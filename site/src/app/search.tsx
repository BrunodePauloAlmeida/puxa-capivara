"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { IndexRow } from "@/lib/types.ts";

const MIN_LENGTH = 2;

export function Thumbnail({ person }: { person: Pick<IndexRow, "id" | "photo" | "initials"> }) {
  return person.photo ? (
    // Photos come out of the pipeline already downscaled; next/image would add nothing here.
    <img className="thumbnail" src={`/foto/${person.id}`} alt="" width={42} height={56} loading="lazy" />
  ) : (
    <span className="thumbnail" aria-hidden="true">
      {person.initials}
    </span>
  );
}

export function Search({ initialQuery, initialResults }: { initialQuery: string; initialResults: IndexRow[] }) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState(initialResults);
  const [searched, setSearched] = useState(initialQuery.trim().length >= MIN_LENGTH ? initialQuery.trim() : "");
  const [error, setError] = useState(false);
  const list = useRef<HTMLUListElement>(null);
  const field = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (q === searched) return;
    if (q.length < MIN_LENGTH) {
      setResults([]);
      setSearched("");
      window.history.replaceState(null, "", "/");
      return;
    }
    const controller = new AbortController();
    const debounce = setTimeout(async () => {
      try {
        const r = await fetch(`/api/busca?q=${encodeURIComponent(q)}`, { signal: controller.signal });
        if (!r.ok) throw new Error(String(r.status));
        const data = (await r.json()) as { results: IndexRow[] };
        setResults(data.results);
        setSearched(q);
        setError(false);
        window.history.replaceState(null, "", `/?q=${encodeURIComponent(q)}`);
      } catch (e) {
        if ((e as Error).name !== "AbortError") setError(true);
      }
    }, 150);
    return () => {
      clearTimeout(debounce);
      controller.abort();
    };
  }, [query, searched]);

  const links = () => Array.from(list.current?.querySelectorAll("a") ?? []);

  function onFieldKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" && results.length) {
      e.preventDefault();
      links()[0]?.focus();
    } else if (e.key === "Escape") {
      setQuery("");
    }
  }

  function onListKeyDown(e: React.KeyboardEvent<HTMLUListElement>) {
    const all = links();
    const current = all.indexOf(document.activeElement as HTMLAnchorElement);
    if (e.key === "ArrowDown" && current < all.length - 1) {
      e.preventDefault();
      all[current + 1].focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (current <= 0) field.current?.focus();
      else all[current - 1].focus();
    }
  }

  const q = query.trim();
  let status = "";
  if (error) status = "Não foi possível buscar agora. Tente de novo em instantes.";
  else if (q.length > 0 && q.length < MIN_LENGTH) status = "Digite pelo menos duas letras.";
  else if (searched && q === searched)
    status =
      results.length === 0
        ? `Nenhum nome encontrado para "${searched}".`
        : results.length === 1
          ? "1 resultado"
          : `${results.length} resultados${results.length === 20 ? " (os 20 mais próximos)" : ""}`;

  return (
    <div className="search">
      <form
        role="search"
        action="/"
        onSubmit={(e) => {
          e.preventDefault();
          if (results[0] && q === searched) router.push(`/ficha/${results[0].id}`);
        }}
      >
        <label htmlFor="q">Nome do político</label>
        <div className="field">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            ref={field}
            id="q"
            name="q"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onFieldKeyDown}
            placeholder="Ex.: Erika Hilton, Tarcísio, Davi Alcolumbre"
            autoComplete="off"
            autoCapitalize="words"
            spellCheck={false}
            enterKeyHint="search"
            aria-describedby="search-status"
            autoFocus={!initialQuery}
          />
        </div>
      </form>
      <p id="search-status" className="status" aria-live="polite">
        {status}
      </p>
      {results.length > 0 && (
        <ul className="results" ref={list} onKeyDown={onListKeyDown} aria-label="Resultados da busca">
          {results.map((p) => (
            <li key={p.id}>
              <Link className="result" href={`/ficha/${p.id}`} prefetch={false}>
                <Thumbnail person={p} />
                <span>
                  <strong>{p.name}</strong>
                  <span className="role">{[p.role, p.party_state].filter(Boolean).join(" · ")}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
