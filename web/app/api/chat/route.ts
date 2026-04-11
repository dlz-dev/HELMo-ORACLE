import { NextRequest } from "next/server";
import { getServerUserId } from "@/lib/server-auth";

export const runtime = "nodejs"; // Important : pas edge, on consomme du SSE

export async function POST(req: NextRequest) {
  const userId = await getServerUserId();
  const body = await req.json();

  const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

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

  const backendResponse = await fetch(`${backendUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(backendBody),
  });

  if (!backendResponse.ok || !backendResponse.body) {
    const error = await backendResponse.text();
    return new Response(JSON.stringify({ error }), {
      status: backendResponse.status,
    });
  }

  // Capture le session_id depuis les headers du backend
  const sessionIdFromHeader = backendResponse.headers.get("X-Session-Id") || "";

  const enc = new TextEncoder();

  // Transforme le SSE FastAPI → AI SDK Data Stream Protocol
  const stream = new ReadableStream({
    async start(controller) {
      if (!backendResponse.body) {
        controller.enqueue(
          enc.encode(
            `3:${JSON.stringify("Erreur: Corps de réponse backend vide")}\n`,
          ),
        );
        controller.enqueue(enc.encode(`d:{"finishReason":"error"}\n`));
        controller.close();
        return;
      }

      const reader = backendResponse.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (value) {
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

              if (event.type === "step") {
                controller.enqueue(
                  enc.encode(
                    `2:${JSON.stringify([{ pipelineStep: event.step }])}\n`,
                  ),
                );
              } else if (event.type === "text") {
                controller.enqueue(
                  enc.encode(`0:${JSON.stringify(event.content)}\n`),
                );
              } else if (event.type === "cot") {
                const cotResults = event.results as unknown[];
                controller.enqueue(
                  enc.encode(`2:${JSON.stringify([{ cotResults }])}\n`),
                );
              } else if (event.type === "done") {
                controller.enqueue(
                  enc.encode(
                    `d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n`,
                  ),
                );
              } else if (event.type === "error") {
                controller.enqueue(
                  enc.encode(
                    `3:${JSON.stringify((event.message as string) || "Erreur serveur")}\n`,
                  ),
                );
                controller.enqueue(enc.encode(`d:{"finishReason":"error"}\n`));
              }
            }
          }

          if (done) {
            // Traite le dernier morceau de buffer si présent
            if (buffer.startsWith("data: ")) {
              const raw = buffer.slice(6).trim();
              try {
                const event = JSON.parse(raw);
                if (event.type === "done") {
                  controller.enqueue(
                    enc.encode(
                      `d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n`,
                    ),
                  );
                }
              } catch {}
            }
            break;
          }
        }
      } catch (err) {
        console.error("Error in stream processing:", err);
        controller.enqueue(
          enc.encode(`3:${JSON.stringify("Stream processing error")}\n`),
        );
        controller.enqueue(enc.encode(`d:{"finishReason":"error"}\n`));
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
      "X-Session-Id": sessionIdFromHeader,
    },
  });
}
