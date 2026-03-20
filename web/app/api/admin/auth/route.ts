import { NextResponse } from "next/server";
import { timingSafeEqual, createHash } from "crypto";

export async function POST(req: Request) {
  const { password } = await req.json();

  const expected =
    process.env.ADMIN_PASSWORD ||
    process.env.NEXT_PUBLIC_ADMIN_PASSWORD ||
    "oracle";

  // Comparaison résistante aux timing attacks via hash SHA-256
  const a = createHash("sha256")
    .update(password || "")
    .digest();
  const b = createHash("sha256").update(expected).digest();

  if (a.length === b.length && timingSafeEqual(a, b)) {
    return NextResponse.json({ ok: true });
  }

  return NextResponse.json({ ok: false }, { status: 401 });
}
