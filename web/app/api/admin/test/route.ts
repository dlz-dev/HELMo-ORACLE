import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const { provider, model, message, temperature, k_final } = body;

  if (!provider || !model || !message) {
    return NextResponse.json(
      { error: "Provider, model, and message are required" },
      { status: 400 },
    );
  }

  const backendUrl = process.env.ORACLE_API_URL || "http://127.0.0.1:8000";
  const apiKey = process.env.API_SECRET_KEY || "";

  try {
    const res = await fetch(`${backendUrl}/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Api-Key": apiKey,
      },
      body: JSON.stringify({
        message,
        provider,
        model,
        temperature: temperature || 0,
        k_final: k_final || 1,
      }),
    });

    const text = await res.text();
    if (!text) {
      return NextResponse.json(
        { error: "Réponse vide du backend" },
        { status: 500 },
      );
    }

    const data = JSON.parse(text);
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Erreur de connexion au backend" },
      { status: 500 },
    );
  }
}
