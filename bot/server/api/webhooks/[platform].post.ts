/**
 * POST /api/webhooks/:platform
 *
 * Point d'entrée unique pour les webhooks de toutes les plateformes.
 * Discord envoie ses interactions ici (configuré dans le portail développeur).
 *
 * Le Chat SDK vérifie la signature Ed25519 de Discord automatiquement
 * via DISCORD_PUBLIC_KEY, puis route l'événement vers les handlers du bot.
 *
 * waitUntil() permet de répondre 200 immédiatement à Discord (deadline 3s)
 * pendant que le traitement IA continue en arrière-plan.
 */

import { getBot } from "~/server/lib/bot";

export default defineEventHandler(async (event) => {
  const platform = getRouterParam(event, "platform") as string;

  const bot = getBot();
  const adapter = (bot as any).adapters?.[platform];

  if (!adapter) {
    throw createError({ statusCode: 404, message: `Unknown platform: ${platform}` });
  }

  const body = await readRawBody(event);
  const headers = Object.fromEntries(
    Object.entries(getRequestHeaders(event)).map(([k, v]) => [k, v ?? ""])
  );

  // Traitement asynchrone : répond à Discord avant la deadline de 3s
  // puis continue le pipeline IA sans bloquer la réponse HTTP
  event.waitUntil(
    adapter.handleRequest({ body, headers })
  );

  // Discord attend un 200 immédiat pour valider le webhook
  return new Response(null, { status: 200 });
});
