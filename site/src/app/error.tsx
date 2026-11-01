"use client";

export default function Erro({ reset }: { error: Error; reset: () => void }) {
  return (
    <section className="vazio-pagina">
      <h1>Algo deu errado</h1>
      <p className="nota">Não conseguimos carregar os dados agora. Tente de novo em instantes.</p>
      <p>
        <button type="button" className="botao" onClick={reset}>
          Tentar de novo
        </button>
      </p>
    </section>
  );
}
