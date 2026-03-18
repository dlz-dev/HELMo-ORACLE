import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const { folder_path } = body;

  if (!folder_path) {
    return NextResponse.json({ error: "Folder path is required" }, { status: 400 });
  }

  const backendUrl = process.env.ORACLE_API_URL || "http://127.0.0.1:8000";
  const apiKey = process.env.API_SECRET_KEY || "";

  try {
    const res = await fetch(`${backendUrl}/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Api-Key": apiKey,
      },
      body: JSON.stringify({ folder_path }),
    });

    const text = await res.text();
    if (!text) {
      return NextResponse.json({ error: "Réponse vide du backend" }, { status: 500 });
    }
    const data = JSON.parse(text);
    if (!res.ok) return NextResponse.json(data, { status: res.status });
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Erreur de connexion au backend" }, { status: 500 });
  }
}