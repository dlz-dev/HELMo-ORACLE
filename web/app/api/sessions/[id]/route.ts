import { NextResponse } from "next/server";
import { getServerUserId } from "@/lib/server-auth";

const BACKEND = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

// GET /api/sessions/[id]
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const userId = await getServerUserId();
    const url = userId
      ? `${BACKEND}/sessions/${id}?user_id=${encodeURIComponent(userId)}`
      : `${BACKEND}/sessions/${id}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok)
      return NextResponse.json(
        { error: "Session non trouvée" },
        { status: 404 },
      );
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Erreur backend" }, { status: 500 });
  }
}

// DELETE /api/sessions/[id]
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const userId = await getServerUserId();
    const url = userId
      ? `${BACKEND}/sessions/${id}?user_id=${encodeURIComponent(userId)}`
      : `${BACKEND}/sessions/${id}`;
    await fetch(url, { method: "DELETE" });
    return NextResponse.json({ deleted: id });
  } catch {
    return NextResponse.json({ error: "Erreur backend" }, { status: 500 });
  }
}
