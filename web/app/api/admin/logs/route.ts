import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const lines = searchParams.get("lines") ?? "100";
  const level = searchParams.get("level") ?? "";

  try {
    const url = new URL(`${process.env.BACKEND_API_URL}/logs`);
    url.searchParams.set("lines", lines);
    if (level) url.searchParams.set("level", level);

    const res = await fetch(url.toString(), {
      headers: {
        "X-API-Key": process.env.API_SECRET_KEY ?? "",
      },
    });

    if (!res.ok) throw new Error(`Backend error: ${res.status}`);

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: "Erreur récupération logs", details: error.message },
      { status: 500 },
    );
  }
}
