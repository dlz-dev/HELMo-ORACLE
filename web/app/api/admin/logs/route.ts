import { NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
const API_KEY = process.env.API_SECRET_KEY || "";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const lines = searchParams.get("lines") || "100";
  try {
    const res = await fetch(`${BACKEND}/logs?lines=${lines}`, {
      headers: { "X-Api-Key": API_KEY },
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ logs: [], total: 0 }, { status: 500 });
  }
}

export async function DELETE() {
  try {
    await fetch(`${BACKEND}/logs`, { method: "DELETE", headers: { "X-Api-Key": API_KEY } });
    return NextResponse.json({ cleared: true });
  } catch {
    return NextResponse.json({ error: "Erreur backend" }, { status: 500 });
  }
}
