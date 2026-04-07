/**
 * HELMo Oracle — Bot Core
 *
 * Initialise le Chat SDK avec l'adaptateur Discord et la persistance Redis.
 * L'agent utilise Groq (primaire) ou Anthropic (fallback) + le serveur MCP
 * HELMo Oracle pour répondre aux questions sur la base de connaissances Dofus.
 *
 * Pour ajouter WhatsApp plus tard :
 *   import { createWhatsAppAdapter } from "@chat-adapter/whatsapp";
 *   adapters: { discord: createDiscordAdapter(), whatsapp: createWhatsAppAdapter() }
 */

import { Chat, toAiMessages } from "chat";
import { createDiscordAdapter } from "@chat-adapter/discord";
import { createRedisState } from "@chat-adapter/state-redis";
import { createGroq } from "@ai-sdk/groq";
import { createAnthropic } from "@ai-sdk/anthropic";
import { experimental_createMCPClient as createMCPClient, streamText, type CoreMessage } from "ai";

// ── Singleton ──────────────────────────────────────────────────────────────────
let _bot: Chat | null = null;

export function getBot(): Chat {
  if (_bot) return _bot;
  throw new Error("Bot not initialized. Call initBot() first.");
}

// ── Initialisation ─────────────────────────────────────────────────────────────
export async function initBot(config: {
  mcpServerUrl: string;
  groqApiKey: string;
  anthropicApiKey?: string;
}): Promise<Chat> {
  if (_bot) return _bot;

  // Groq primaire — llama-3.3-70b est rapide, gratuit et supporte le tool use
  const groq = createGroq({ apiKey: config.groqApiKey });
  // Anthropic optionnel (laisser vide si non utilisé)
  const anthropic = config.anthropicApiKey
    ? createAnthropic({ apiKey: config.anthropicApiKey })
    : null;

  const model = groq("llama-3.3-70b-versatile");

  // ── MCP Client → outils HELMo Oracle ────────────────────────────────────────
  // Le client MCP se connecte au serveur FastAPI exposé sur /mcp.
  // Il expose automatiquement search_knowledge_base et list_sources comme tools.
  const mcpClient = await createMCPClient({
    transport: {
      type: "sse",
      url: config.mcpServerUrl,
    },
  });
  const mcpTools = await mcpClient.tools();

  // ── Chat SDK ─────────────────────────────────────────────────────────────────
  _bot = new Chat({
    userName: "helmo-oracle",
    adapters: {
      discord: createDiscordAdapter(),
      // whatsapp: createWhatsAppAdapter(), // ← décommenter quand prêt
    },
    state: createRedisState(),
  });

  // ── Événement : nouvelle mention (@helmo-oracle) ────────────────────────────
  // Le bot s'abonne au fil et confirme sa présence.
  _bot.onNewMention(async (thread) => {
    await thread.subscribe();
    await thread.post(
      "Bonjour, je suis HELMo Oracle ! Je consulte les Archives Sacrées pour répondre à tes questions Dofus. ⚔️"
    );
  });

  // ── Événement : nouveau message dans un fil suivi ───────────────────────────
  // Récupère l'historique, stream la réponse Claude avec les outils MCP.
  _bot.onSubscribedMessage(async (thread, message) => {
    // Récupère les 20 derniers messages pour le contexte multi-tour
    const { messages: raw } = await thread.adapter.fetchMessages(thread.id, {
      limit: 20,
    });
    const history = await toAiMessages(raw);

    // Stream Groq avec les outils MCP injectés directement
    const result = await streamText({
      model,
      system:
        "Tu es HELMo Oracle, expert en Dofus. " +
        "Utilise search_knowledge_base pour interroger la base de connaissances avant de répondre. " +
        "Sois précis, concis, et cite tes sources.",
      messages: history as unknown as CoreMessage[],
      tools: mcpTools,         // ← outils MCP : search_knowledge_base, list_sources
      maxSteps: 5,              // permet plusieurs appels d'outils en chaîne
    });

    // Poste le stream directement — le SDK gère les mises à jour progressives
    await thread.post(result.fullStream);
  });

  return _bot;
}
