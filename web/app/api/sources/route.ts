import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${backendUrl}/archives`, {
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: "Erreur backend" },
        { status: res.status },
      );
    }

    const data = await res.json();
    // Le backend retourne { sources: [...] }
    return NextResponse.json({ sources: data.sources ?? [] });
  } catch (error) {
    return NextResponse.json(
      { error: "Impossible de charger les sources" },
      { status: 500 },
    );
  }
}
