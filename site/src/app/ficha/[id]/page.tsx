import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { readPerson } from "@/lib/data.ts";
import type { VoteRow } from "@/lib/types.ts";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const person = await readPerson((await params).id);
  if (!person) return { title: "Não encontrado" };
  return {
    title: person.name,
    description: `${person.roles[0] ?? ""}. Votações-chave e produção legislativa, com dados oficiais.`,
  };
}

function Vote({ v, featured = false }: { v: VoteRow; featured?: boolean }) {
  const context = [
    [v.house, v.date].filter(Boolean).join(", "),
    `Sim = ${v.yes_means}`,
    v.outcome && `Resultado: ${v.outcome}`,
  ].filter(Boolean);
  return (
    <div className={`vote-row${featured ? " featured" : ""}`}>
      <div>
        <div className="title">{v.title}</div>
        <div className="sub">{context.join(" · ")}</div>
      </div>
      <div className="vote">
        <span className={`chip ${v.class}${featured ? " large" : ""}`}>{v.vote}</span>
        {v.detail && <span className="detail">{v.detail}</span>}
      </div>
    </div>
  );
}

function Pending({ title, text, label }: { title: string; text: string; label: string }) {
  return (
    <div className="vote-row featured">
      <div>
        <div className="title">{title}</div>
        <div className="sub">{text}</div>
      </div>
      <div className="vote">
        <span className="chip empty">{label}</span>
      </div>
    </div>
  );
}

export default async function Profile({ params }: Props) {
  const { id } = await params;
  const p = await readPerson(id);
  if (!p) notFound();

  const showCivilName = p.civil_name && p.civil_name.toLowerCase() !== p.name.toLowerCase();

  return (
    <article>
      <Link href="/" className="back">
        ← Nova busca
      </Link>

      <header className="identity">
        {p.has_photo ? (
          <img className="portrait" src={`/foto/${p.id}`} alt={`Foto de ${p.name}`} width={120} height={160} />
        ) : (
          <div className="portrait" aria-hidden="true">
            {p.initials}
          </div>
        )}
        <div>
          <h1>{p.name}</h1>
          {showCivilName && <p className="civil-name">Nome civil: {p.civil_name}</p>}
          <ul className="roles">
            {p.roles.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          {p.has_pdf && (
            <a className="button" href={`/ficha/${p.id}/pdf`} download>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 19h14"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Exportar PDF
            </a>
          )}
        </div>
      </header>

      <section className="section" aria-labelledby="t-hot-topics">
        <h2 id="t-hot-topics">Temas do momento</h2>
        <div className="box">
          {p.hot_topics.map((v) => (
            <Vote key={`${v.title}-${v.house}`} v={v} featured />
          ))}
          {!p.in_congress && (
            <Pending
              title="Fim da escala 6x1"
              text="Sem mandato atual no Congresso. Votos de mandatos anteriores entram nas próximas versões."
              label="Não se aplica"
            />
          )}
          <Pending
            title="Proibição das bets"
            text="Ainda sem votação nominal no Congresso. Declarações sobre o tema entram na próxima versão."
            label="Em levantamento"
          />
        </div>
      </section>

      {p.votes.length > 0 && (
        <section className="section" aria-labelledby="t-votes">
          <h2 id="t-votes">Votações-chave da legislatura 2023–2027</h2>
          <div className="box">
            {p.votes.map((v) => (
              <Vote key={`${v.title}-${v.house}`} v={v} />
            ))}
          </div>
          <p className="note">
            &ldquo;Sem registro&rdquo;: ausente ou sem mandato na data da votação. Votos de plenário; quando houve
            dois turnos, vale o 1º.
          </p>
        </section>
      )}

      {p.bills ? (
        <section className="section" aria-labelledby="t-bills">
          <h2 id="t-bills">
            Produção legislativa ({p.bills.house}, desde {p.bills.since})
          </h2>
          <div className="stats">
            <div className="stat">
              <b>{p.bills.first_author}</b>projetos como primeiro autor
            </div>
            <div className="stat">
              <b>{p.bills.total}</b>projetos contando coautorias
            </div>
            <div className="stat">
              <b>{p.bills.became_law}</b>viraram lei ou norma, como primeiro autor
            </div>
          </div>
          {p.bills.highlights.length > 0 && (
            <ul className="highlights">
              {p.bills.highlights.map((h) => (
                <li key={h.identifier}>
                  <span className="law">
                    {h.identifier}
                    {h.law && ` → ${h.law}`}
                  </span>
                  {h.summary}
                </li>
              ))}
            </ul>
          )}
          <p className="note">
            Conta projetos de lei, de lei complementar, de decreto legislativo, de resolução e PECs. Assinaturas
            de apoio a PEC não contam como autoria.
          </p>
        </section>
      ) : (
        !p.in_congress && (
          <section className="section" aria-labelledby="t-activity">
            <h2 id="t-activity">Atuação</h2>
            <p className="note">
              Sem mandato atual no Congresso. Mandatos anteriores, patrimônio declarado, financiamento de
              campanha e atos de governo entram nas próximas versões.
            </p>
          </section>
        )
      )}

      <footer className="sources">
        <p>
          <b>Fontes:</b> Câmara dos Deputados, Senado Federal e Tribunal Superior Eleitoral (dados abertos).
          {p.photo_source && ` Foto: ${p.photo_source}.`}
        </p>
        <p>Dados atualizados em {p.generated_at}.</p>
      </footer>
    </article>
  );
}
