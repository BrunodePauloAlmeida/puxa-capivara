import Link from "next/link";

export default function NotFound() {
  return (
    <section className="empty-page">
      <h1>Página não encontrada</h1>
      <p className="note">Esse endereço não corresponde a ninguém do cadastro.</p>
      <p>
        <Link href="/">Voltar para a busca</Link>
      </p>
    </section>
  );
}
