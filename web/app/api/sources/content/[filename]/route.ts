import { NextResponse } from "next/server";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ filename: string }> },
) {
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const { filename: raw } = await params;
  const filename = encodeURIComponent(raw);

  try {
    const res = await fetch(`${backendUrl}/sources/content/${filename}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: "Fichier introuvable" },
        { status: res.status },
      );
    }

    const text = await res.text();
    return new NextResponse(text, {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  } catch {
    return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
  }
}
