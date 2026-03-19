import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const apiKey = process.env.API_SECRET_KEY || "";

  try {
    const res = await fetch(`${backendUrl}/ingest/status`, {
      headers: { "X-Api-Key": apiKey },
      cache: "no-store",
    });

    const text = await res.text();
    if (!text) {
      return NextResponse.json(
        { running: false, last_status: "error", last_message: "Réponse vide du backend" },
        { status: 500 }
      );
    }
    const data = JSON.parse(text);
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { running: false, last_status: "error", last_message: "Impossible de joindre le backend" },
      { status: 500 }
    );
  }
}