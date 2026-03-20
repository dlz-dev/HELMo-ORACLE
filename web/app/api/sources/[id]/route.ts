import { NextRequest, NextResponse } from "next/server";

// DELETE /api/sources/[id]
export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${backendUrl}/api/sources/${id}`, {
      method: "DELETE",
    });

    if (!res.ok) throw new Error("Erreur lors de la suppression");

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Impossible de supprimer la source" },
      { status: 500 },
    );
  }
}
