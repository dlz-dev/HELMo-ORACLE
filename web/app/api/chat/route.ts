import { NextRequest } from "next/server";
import { getServerUserId } from "@/lib/server-auth";

export const runtime = "nodejs"; // Important : pas edge, on consomme du SSE

export async function POST(req: NextRequest) {
  const userId = await getServerUserId();
  const body = await req.json();

  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  const messages: Array<{ role: string; content: string }> = body.messages || [];
  const lastUserMessage = messages.filter((m) => m.role === "user").at(-1);

  if (!lastUserMessage) {
    return new Response(JSON.stringify({ error: "No message provided" }), { status: 400 });
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

  const backendResponse = await fetch(`${backendUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(backendBody),
  });

  if (!backendResponse.ok || !backendResponse.body) {
    const error = await backendResponse.text();
    return new Response(JSON.stringify({ error }), { status: backendResponse.status });
  }

  const enc = new TextEncoder();
  let sessionId = "";

  // Transforme le SSE FastAPI → AI SDK Data Stream Protocol
  const stream = new ReadableStream({
    async start(controller) {
      const reader = backendResponse.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            let event: { type: string; [key: string]: unknown };
            try {
              event = JSON.parse(raw);
            } catch {
              continue;
            }

            if (event.type === "session_id") {
              sessionId = event.session_id as string;
            } else if (event.type === "text") {
              // Format AI SDK Data Stream : "0:\"chunk\"\n"
              controller.enqueue(
                enc.encode(`0:${JSON.stringify(event.content)}\n`)
              );
            } else if (event.type === "cot") {
              const cotResults = event.results as unknown[];
              // Envoie les sources RAG comme data annotation AI SDK : "2:[...]\n"
              controller.enqueue(
                enc.encode(`2:${JSON.stringify([{ cotResults }])}\n`)
              );
            } else if (event.type === "done") {
              controller.enqueue(
                enc.encode(
                  `d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n`
                )
              );
            }
          }
        }
      } finally {
        controller.close();
      }
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
}
