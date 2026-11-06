import { readMeta, searchPeople } from "@/lib/data.ts";

import { Search } from "./search.tsx";

export default async function Home({ searchParams }: { searchParams: Promise<{ q?: string | string[] }> }) {
  const { q } = await searchParams;
  const query = (Array.isArray(q) ? q[0] : q)?.slice(0, 80) ?? "";
  const [meta, initialResults] = await Promise.all([readMeta(), query ? searchPeople(query) : []]);

  return (
    <>
      <section className="hero">
        <h1>Quem é quem na política</h1>
        <p>
          Busque pelo nome e veja, em uma página, como a pessoa votou nos projetos mais importantes, o que
          propôs e o que virou lei. Dá para baixar tudo em PDF.
        </p>
        <Search initialQuery={query} initialResults={initialResults} />
      </section>

      {meta && (
        <section className="panel" aria-labelledby="panel-title">
          <h2 id="panel-title">Quem está aqui</h2>
          <div className="stats">
            <div className="stat">
              <b>{meta.in_office.president}</b>Presidente da República
            </div>
            <div className="stat">
              <b>{meta.in_office.governor}</b>governadores
            </div>
            <div className="stat">
              <b>{meta.in_office.senator}</b>senadores
            </div>
            <div className="stat">
              <b>{meta.in_office.federal_deputy}</b>deputados federais
            </div>
          </div>
          <p className="note">
            Em exercício hoje, mais quem foi eleito em 2026: {meta.people.toLocaleString("pt-BR")} pessoas no
            total. Dados de {meta.generated_at.split("-").reverse().join("/")}.
          </p>
        </section>
      )}
    </>
  );
}
