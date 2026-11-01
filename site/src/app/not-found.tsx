import Link from "next/link";

export default function NaoEncontrado() {
  return (
    <section className="vazio-pagina">
      <h1>Página não encontrada</h1>
      <p className="nota">Esse endereço não corresponde a ninguém do cadastro.</p>
      <p>
        <Link href="/">Voltar para a busca</Link>
      </p>
    </section>
  );
}
