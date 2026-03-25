import { NextRequest } from "next/server";
import { getServerUserId } from "@/lib/server-auth";

export async function POST(req: NextRequest) {
  const userId = await getServerUserId();
  const body = await req.json();

  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  // The Vercel AI SDK sends { messages: [...], ...extras }
  // FastAPI expects { message: str, session_id, user_id, ... }
  const messages: Array<{ role: string; content: string }> =
    body.messages || [];
  const lastUserMessage = messages.filter((m) => m.role === "user").at(-1);

  if (!lastUserMessage) {
    return new Response(JSON.stringify({ error: "No message provided" }), {
      status: 400,
    });
  }

  const backendBody = {
    message: lastUserMessage.content,
    session_id: body.session_id || null,
    user_id: userId || null,
    provider: body.provider || "groq",
    model: body.model || null,
    temperature: body.temperature ?? 0,
    k_final: body.k_final ?? 5,
  };

  try {
    const response = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(backendBody),
    });

    if (!response.ok) {
      const error = await response.text();
      return new Response(JSON.stringify({ error }), {
        status: response.status,
      });
    }

    const data = await response.json();
    const responseText: string = data.response || "";
    const sessionId: string = data.session_id || "";

    // Convert FastAPI JSON response to Vercel AI SDK data stream format
    const enc = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(enc.encode(`0:${JSON.stringify(responseText)}\n`));
        controller.enqueue(
          enc.encode(
            `d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n`,
          ),
        );
        controller.close();
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "X-Vercel-AI-Data-Stream": "v1",
        "Cache-Control": "no-cache",
        "X-Session-Id": sessionId,
      },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: "Erreur de connexion au backend" }),
      { status: 500 },
    );
  }
}
