"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <section className="empty-page">
      <h1>Algo deu errado</h1>
      <p className="note">Não conseguimos carregar os dados agora. Tente de novo em instantes.</p>
      <p>
        <button type="button" className="button" onClick={reset}>
          Tentar de novo
        </button>
      </p>
    </section>
  );
}
