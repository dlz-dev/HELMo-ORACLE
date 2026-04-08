import { NextResponse } from "next/server";

export async function POST() {
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${backendUrl}/ingest/cancel`, {
      method: "POST",
      headers: { "X-Api-Key": process.env.API_SECRET_KEY || "" },
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Erreur de connexion au backend" },
      { status: 500 },
    );
  }
}
