import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Erreur backend" }), { status: response.status });
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "X-Vercel-AI-Data-Stream": "v1",
        "Cache-Control": "no-cache",
        "X-Session-Id": response.headers.get("X-Session-Id") || "",
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: "Erreur de connexion au backend" }), { status: 500 });
  }
}