import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const formData = await request.formData();

    const res = await fetch(`${backendUrl}/ingest`, {
      method: "POST",
      headers: { "X-Api-Key": process.env.API_SECRET_KEY || "" },
      body: formData,
    });

    const text = await res.text();
    if (!text) {
      return NextResponse.json(
        { error: "Réponse vide du backend" },
        { status: 500 },
      );
    }
    const data = JSON.parse(text);
    if (!res.ok) return NextResponse.json(data, { status: res.status });
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Erreur de connexion au backend" },
      { status: 500 },
    );
  }
}
