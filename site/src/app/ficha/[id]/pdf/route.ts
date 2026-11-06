import { readBinary } from "@/lib/data.ts";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const pdf = await readBinary("pdf", id, "pdf");
  if (!pdf) return new Response("PDF não encontrado", { status: 404 });
  return new Response(new Uint8Array(pdf), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="puxa-capivara-${id}.pdf"`,
      "Cache-Control": "public, max-age=3600, s-maxage=86400",
    },
  });
}
