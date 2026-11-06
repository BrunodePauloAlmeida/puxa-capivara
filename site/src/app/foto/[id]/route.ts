import { readBinary } from "@/lib/data.ts";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const photo = await readBinary("photos", id, "jpg");
  if (!photo) return new Response("Foto não encontrada", { status: 404 });
  return new Response(new Uint8Array(photo), {
    headers: {
      "Content-Type": "image/jpeg",
      "Cache-Control": "public, max-age=86400, s-maxage=604800",
    },
  });
}
