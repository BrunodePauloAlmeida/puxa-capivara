import "@fontsource-variable/inter";
import "./globals.css";

import type { Metadata, Viewport } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: { default: "puxa-capivara", template: "%s · puxa-capivara" },
  description:
    "Busque um político pelo nome e veja, em uma página, como votou nos projetos mais importantes e o que propôs. Dados oficiais da Câmara, do Senado e do TSE.",
  // Rascunho v1: dados ainda em validação, então o site fica fora dos buscadores por enquanto.
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#121417" },
  ],
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="topo">
          <div className="conteudo topo-linha">
            <Link href="/" className="marca">
              puxa-capivara
            </Link>
            <span className="selo">rascunho v1</span>
          </div>
        </header>
        <main className="conteudo">{children}</main>
        <footer className="rodape">
          <div className="conteudo">
            <p>
              Dados abertos da Câmara dos Deputados, do Senado Federal e do Tribunal Superior Eleitoral. Cada
              informação vem de fonte oficial.
            </p>
            <p>
              Rascunho v1: os dados estão em validação e podem conter erros. Ainda não entram patrimônio,
              financiamento de campanha, processos e declarações.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
