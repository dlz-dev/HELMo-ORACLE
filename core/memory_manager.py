"""
core/memory_manager.py

Implements a SummaryBuffer memory strategy compatible with LangGraph's
create_react_agent — without using LangChain's ConversationSummaryBufferMemory
(which is designed for classic chains, not agents).

How it works:
─────────────────────────────────────────────────────────────────────────────
  Full history (all messages in session)
       │
       ▼
  ┌────────────────────────────────────┐
  │  SUMMARY (condensed older turns)  │  ← injected into system prompt
  ├────────────────────────────────────┤
  │  RECENT MESSAGES (intact)         │  ← passed verbatim to the agent
  │  last N messages ≤ max_tokens     │
  └────────────────────────────────────┘

When the recent window exceeds `max_recent_tokens`, the oldest recent messages
are summarized and merged into the running summary via an LLM call.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

# Approximate token count (1 token ≈ 4 chars — conservative estimate)
def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def _messages_tokens(messages: list[dict]) -> int:
    return sum(_estimate_tokens(m.get("content", "")) for m in messages)


# ─────────────────────────────────────────────────────────────────
# Summarization
# ─────────────────────────────────────────────────────────────────

_SUMMARY_PROMPT = """You are summarizing a conversation between a user and an AI Oracle specialized in the Dofus game.

Your task: write a CONCISE summary (5-10 sentences max) of the conversation below.
Focus on:
- The user's main topics and questions
- Key information the Oracle provided
- Any preferences or context the user mentioned (character class, level, goals...)

This summary will be injected into future conversations so the Oracle remembers the context.
Write in the same language as the conversation. Be factual, not narrative.

Existing summary (if any):
{existing_summary}

New messages to integrate:
{new_messages}

Write the updated summary now:"""


def _format_messages_for_summary(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = "User" if m["role"] == "user" else "Oracle"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def summarize_messages(
    messages_to_summarize: list[dict],
    existing_summary: str,
    llm: BaseChatModel,
) -> str:
    """
    Calls the LLM to produce an updated summary merging existing_summary
    with the newly overflowing messages.
    Returns the new summary string.
    """
    prompt_text = _SUMMARY_PROMPT.format(
        existing_summary=existing_summary or "(none yet)",
        new_messages=_format_messages_for_summary(messages_to_summarize),
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt_text)])
        return response.content.strip()
    except Exception as e:
        # Summarization failure is non-blocking — return old summary
        print(f"⚠️ Memory summarization failed: {e}")
        return existing_summary


# ─────────────────────────────────────────────────────────────────
# MemoryManager
# ─────────────────────────────────────────────────────────────────

class MemoryManager:
    """
    Manages the summary-buffer memory strategy for a session.

    Args:
        max_recent_tokens:  Token budget for recent messages passed to the agent.
                            When exceeded, oldest messages are summarized.
                            Default: 2000 tokens (~8000 chars) — safe for all models.
        min_recent_messages: Always keep at least this many recent messages intact,
                             regardless of token count. Prevents over-summarization.
    """

    def __init__(
        self,
        max_recent_tokens: int = 2000,
        min_recent_messages: int = 4,
    ):
        self.max_recent_tokens = max_recent_tokens
        self.min_recent_messages = min_recent_messages

    def needs_summarization(self, messages: list[dict], current_summary: str) -> bool:
        """Returns True if the recent messages exceed the token budget."""
        recent = self._get_recent_window(messages)
        return _messages_tokens(recent) > self.max_recent_tokens

    def _get_recent_window(self, messages: list[dict]) -> list[dict]:
        """
        Returns the recent messages that fit within the token budget,
        always keeping at least min_recent_messages.
        """
        if len(messages) <= self.min_recent_messages:
            return messages

        # Walk backwards from the end, accumulate until budget exceeded
        recent = []
        tokens = 0
        for msg in reversed(messages):
            msg_tokens = _estimate_tokens(msg.get("content", ""))
            if tokens + msg_tokens > self.max_recent_tokens and len(recent) >= self.min_recent_messages:
                break
            recent.insert(0, msg)
            tokens += msg_tokens

        return recent

    def compress(
        self,
        session: dict,
        llm: BaseChatModel,
    ) -> dict:
        """
        Compresses the session memory:
        1. Identifies messages that overflow the recent window.
        2. Calls the LLM to summarize them into session["summary"].
        3. Removes the summarized messages from session["messages"].

        Returns the updated session dict.
        """
        messages = session.get("messages", [])
        recent = self._get_recent_window(messages)

        # Messages that will be summarized = everything NOT in recent
        to_summarize = messages[: len(messages) - len(recent)]

        if not to_summarize:
            return session  # Nothing to compress

        print(f"🧠 Compressing {len(to_summarize)} messages into summary...")

        new_summary = summarize_messages(
            messages_to_summarize=to_summarize,
            existing_summary=session.get("summary", ""),
            llm=llm,
        )

        session["summary"] = new_summary
        session["messages"] = recent  # Keep only recent messages
        return session

    def build_agent_input(
        self,
        session: dict,
        base_system_prompt: str,
    ) -> tuple[str, list[tuple[str, str]]]:
        """
        Prepares the inputs for create_react_agent:

        Returns:
            enriched_prompt : system prompt enriched with the memory summary
            history         : list of (role, content) tuples for recent messages
        """
        summary = session.get("summary", "")
        messages = session.get("messages", [])
        recent = self._get_recent_window(messages)

        # Enrich system prompt with summary if it exists
        if summary:
            enriched_prompt = (
                f"{base_system_prompt}\n\n"
                f"═══════════════════════════════════\n"
                f"MEMORY — Summary of previous exchanges:\n"
                f"{summary}\n"
                f"═══════════════════════════════════\n"
                f"(The recent messages below are the continuation of this conversation.)"
            )
        else:
            enriched_prompt = base_system_prompt

        # Build history tuples from recent messages only
        history = [
            ("user" if m["role"] == "user" else "assistant", m["content"])
            for m in recent
        ]

        return enriched_prompt, history