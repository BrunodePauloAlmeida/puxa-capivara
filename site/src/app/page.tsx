import { lerMeta, pesquisar } from "@/lib/dados.ts";

import { Busca } from "./busca.tsx";

export default async function Inicio({ searchParams }: { searchParams: Promise<{ q?: string | string[] }> }) {
  const { q } = await searchParams;
  const consulta = (Array.isArray(q) ? q[0] : q)?.slice(0, 80) ?? "";
  const [meta, iniciais] = await Promise.all([lerMeta(), consulta ? pesquisar(consulta) : []]);

  return (
    <>
      <section className="capa">
        <h1>Quem é quem na política</h1>
        <p>
          Busque pelo nome e veja, em uma página, como a pessoa votou nos projetos mais importantes, o que
          propôs e o que virou lei. Dá para baixar tudo em PDF.
        </p>
        <Busca consultaInicial={consulta} iniciais={iniciais} />
      </section>

      {meta && (
        <section className="painel" aria-labelledby="titulo-painel">
          <h2 id="titulo-painel">Quem está aqui</h2>
          <div className="numeros">
            <div className="numero">
              <b>{meta.em_exercicio.presidente}</b>Presidente da República
            </div>
            <div className="numero">
              <b>{meta.em_exercicio.governador}</b>governadores
            </div>
            <div className="numero">
              <b>{meta.em_exercicio.senador}</b>senadores
            </div>
            <div className="numero">
              <b>{meta.em_exercicio.deputado_federal}</b>deputados federais
            </div>
          </div>
          <p className="nota">
            Em exercício hoje, mais quem foi eleito em 2026: {meta.pessoas.toLocaleString("pt-BR")} pessoas no
            total. Dados de {meta.gerado_em.split("-").reverse().join("/")}.
          </p>
        </section>
      )}
    </>
  );
}
