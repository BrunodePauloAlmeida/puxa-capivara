import { searchPeople } from "@/lib/data.ts";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get("q") ?? "";
  const results = await searchPeople(query.slice(0, 80));
  return Response.json(
    { results },
    { headers: { "Cache-Control": "public, max-age=60, s-maxage=600" } },
  );
}
