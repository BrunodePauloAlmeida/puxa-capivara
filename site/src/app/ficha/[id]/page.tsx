import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { lerPessoa } from "@/lib/dados.ts";
import type { LinhaVoto } from "@/lib/tipos.ts";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const pessoa = await lerPessoa((await params).id);
  if (!pessoa) return { title: "Não encontrado" };
  return {
    title: pessoa.nome,
    description: `${pessoa.cargos[0] ?? ""}. Votações-chave e produção legislativa, com dados oficiais.`,
  };
}

function Voto({ v, destaque = false }: { v: LinhaVoto; destaque?: boolean }) {
  const contexto = [
    [v.casa, v.data].filter(Boolean).join(", "),
    `Sim = ${v.significado_sim}`,
    v.desfecho && `Resultado: ${v.desfecho}`,
  ].filter(Boolean);
  return (
    <div className={`linha-voto${destaque ? " destaque" : ""}`}>
      <div>
        <div className="titulo">{v.titulo}</div>
        <div className="sub">{contexto.join(" · ")}</div>
      </div>
      <div className="voto">
        <span className={`chip ${v.classe}${destaque ? " grande" : ""}`}>{v.voto}</span>
        {v.detalhe && <span className="detalhe">{v.detalhe}</span>}
      </div>
    </div>
  );
}

function Pendente({ titulo, texto, rotulo }: { titulo: string; texto: string; rotulo: string }) {
  return (
    <div className="linha-voto destaque">
      <div>
        <div className="titulo">{titulo}</div>
        <div className="sub">{texto}</div>
      </div>
      <div className="voto">
        <span className="chip vazio">{rotulo}</span>
      </div>
    </div>
  );
}

export default async function Ficha({ params }: Props) {
  const { id } = await params;
  const p = await lerPessoa(id);
  if (!p) notFound();

  const mostrarNomeCivil = p.nome_civil && p.nome_civil.toLowerCase() !== p.nome.toLowerCase();

  return (
    <article>
      <Link href="/" className="voltar">
        ← Nova busca
      </Link>

      <header className="identidade">
        {p.tem_foto ? (
          <img className="retrato" src={`/foto/${p.id}`} alt={`Foto de ${p.nome}`} width={120} height={160} />
        ) : (
          <div className="retrato" aria-hidden="true">
            {p.iniciais}
          </div>
        )}
        <div>
          <h1>{p.nome}</h1>
          {mostrarNomeCivil && <p className="nome-civil">Nome civil: {p.nome_civil}</p>}
          <ul className="cargos">
            {p.cargos.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          {p.tem_pdf && (
            <a className="botao" href={`/ficha/${p.id}/pdf`} download>
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

      <section className="secao" aria-labelledby="t-momento">
        <h2 id="t-momento">Temas do momento</h2>
        <div className="caixa">
          {p.temas_do_momento.map((v) => (
            <Voto key={`${v.titulo}-${v.casa}`} v={v} destaque />
          ))}
          {!p.tem_congresso && (
            <Pendente
              titulo="Fim da escala 6x1"
              texto="Sem mandato atual no Congresso. Votos de mandatos anteriores entram nas próximas versões."
              rotulo="Não se aplica"
            />
          )}
          <Pendente
            titulo="Proibição das bets"
            texto="Ainda sem votação nominal no Congresso. Declarações sobre o tema entram na próxima versão."
            rotulo="Em levantamento"
          />
        </div>
      </section>

      {p.votacoes.length > 0 && (
        <section className="secao" aria-labelledby="t-votacoes">
          <h2 id="t-votacoes">Votações-chave da legislatura 2023–2027</h2>
          <div className="caixa">
            {p.votacoes.map((v) => (
              <Voto key={`${v.titulo}-${v.casa}`} v={v} />
            ))}
          </div>
          <p className="nota">
            &ldquo;Sem registro&rdquo;: ausente ou sem mandato na data da votação. Votos de plenário; quando houve
            dois turnos, vale o 1º.
          </p>
        </section>
      )}

      {p.producao ? (
        <section className="secao" aria-labelledby="t-producao">
          <h2 id="t-producao">
            Produção legislativa ({p.producao.casa}, desde {p.producao.desde})
          </h2>
          <div className="numeros">
            <div className="numero">
              <b>{p.producao.primeiro_autor}</b>projetos como primeiro autor
            </div>
            <div className="numero">
              <b>{p.producao.total}</b>projetos contando coautorias
            </div>
            <div className="numero">
              <b>{p.producao.viraram_norma}</b>viraram lei ou norma, como primeiro autor
            </div>
          </div>
          {p.producao.destaques.length > 0 && (
            <ul className="destaques">
              {p.producao.destaques.map((d) => (
                <li key={d.identificacao}>
                  <span className="norma">
                    {d.identificacao}
                    {d.norma && ` → ${d.norma}`}
                  </span>
                  {d.ementa}
                </li>
              ))}
            </ul>
          )}
          <p className="nota">
            Conta projetos de lei, de lei complementar, de decreto legislativo, de resolução e PECs. Assinaturas
            de apoio a PEC não contam como autoria.
          </p>
        </section>
      ) : (
        !p.tem_congresso && (
          <section className="secao" aria-labelledby="t-atuacao">
            <h2 id="t-atuacao">Atuação</h2>
            <p className="nota">
              Sem mandato atual no Congresso. Mandatos anteriores, patrimônio declarado, financiamento de
              campanha e atos de governo entram nas próximas versões.
            </p>
          </section>
        )
      )}

      <footer className="fontes">
        <p>
          <b>Fontes:</b> Câmara dos Deputados, Senado Federal e Tribunal Superior Eleitoral (dados abertos).
          {p.fonte_foto && ` Foto: ${p.fonte_foto}.`}
        </p>
        <p>Dados atualizados em {p.gerado_em}.</p>
      </footer>
    </article>
  );
}
