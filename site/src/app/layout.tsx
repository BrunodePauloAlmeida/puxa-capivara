import "@fontsource-variable/inter";
import "./globals.css";

import type { Metadata, Viewport } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: { default: "puxa-capivara", template: "%s · puxa-capivara" },
  description:
    "Busque um político pelo nome e veja, em uma página, como votou nos projetos mais importantes e o que propôs. Dados oficiais da Câmara, do Senado e do TSE.",
  // Draft v1: data still being validated, so the site stays out of search engines for now.
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
        <header className="site-header">
          <div className="container site-header-row">
            <Link href="/" className="brand">
              puxa-capivara
            </Link>
            <span className="badge">rascunho v1</span>
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="site-footer">
          <div className="container">
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
