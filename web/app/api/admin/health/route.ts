import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${backendUrl}/health/full`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        status: "error",
        checks: { backend: { status: "error", error: "Backend inaccessible" } },
      },
      { status: 500 },
    );
  }
}
