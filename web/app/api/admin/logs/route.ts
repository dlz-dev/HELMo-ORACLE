import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const lines = searchParams.get("lines") ?? "16";
  const offset = searchParams.get("offset") ?? "0";
  const level = searchParams.get("level") ?? "";
  const source = searchParams.get("source") ?? "";

  try {
    const url = new URL(`${process.env.BACKEND_API_URL}/logs`);
    url.searchParams.set("lines", lines);
    url.searchParams.set("offset", offset);
    if (level) url.searchParams.set("level", level);
    if (source) url.searchParams.set("source", source);

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
