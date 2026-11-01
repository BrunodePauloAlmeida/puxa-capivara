/** Formatos gerados pelo pipeline (`uv run puxa site`, em pipeline/src/puxa/web.py). */

export type Cargo = "presidente" | "governador" | "senador" | "deputado_federal";

export interface LinhaIndice {
  id: string;
  nome: string;
  cargo: string;
  partido_uf: string;
  uf: string | null;
  cargos: Cargo[];
  foto: boolean;
  iniciais: string;
  busca: string;
}

export interface Meta {
  versao: string;
  gerado_em: string;
  pessoas: number;
  em_exercicio: Record<Cargo, number>;
  eleitos_2026: Record<Cargo, number>;
  com_foto: number;
}

export interface LinhaVoto {
  titulo: string;
  significado_sim: string;
  casa: string;
  data: string;
  voto: string;
  classe: "sim" | "nao" | "meio" | "neutro" | "vazio";
  detalhe: string;
  desfecho: string;
}

export interface Producao {
  casa: string;
  desde: string;
  primeiro_autor: number;
  total: number;
  viraram_norma: number;
  destaques: { identificacao: string; norma: string | null; ementa: string }[];
}

export interface Pessoa {
  id: string;
  nome: string;
  nome_civil: string;
  iniciais: string;
  fonte_foto: string | null;
  cargos: string[];
  partido_uf: string;
  temas_do_momento: LinhaVoto[];
  votacoes: LinhaVoto[];
  tem_congresso: boolean;
  producao: Producao | null;
  gerado_em: string;
  versao: string;
  tem_foto: boolean;
  tem_pdf: boolean;
}
