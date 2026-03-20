import { NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

// GET /api/sessions
export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/sessions`, { cache: "no-store" });
    if (!res.ok) return NextResponse.json({ sessions: [] });
    const data = await res.json();
    return NextResponse.json({ sessions: data.sessions ?? [] });
  } catch {
    return NextResponse.json({ sessions: [] });
  }
}

// POST /api/sessions
export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const res = await fetch(`${BACKEND}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Erreur backend" }, { status: 500 });
  }
}
