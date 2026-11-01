import { pesquisar } from "@/lib/dados.ts";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const consulta = new URL(request.url).searchParams.get("q") ?? "";
  const resultados = await pesquisar(consulta.slice(0, 80));
  return Response.json(
    { resultados },
    { headers: { "Cache-Control": "public, max-age=60, s-maxage=600" } },
  );
}
