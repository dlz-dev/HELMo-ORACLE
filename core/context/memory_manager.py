"""
Implements a SummaryBuffer memory strategy compatible with custom agents.

Maintains a sliding window of recent messages up to a maximum token count.
When the window overflows, older messages are summarized and injected into
the system prompt alongside the remaining intact recent messages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from llama_index.core.llms import LLM
from core.utils.utils import _SUMMARY_PROMPT


def _estimate_tokens(text: str) -> int:
    """Provides a conservative token count estimate (1 token ≈ 3 chars)."""
    return max(1, len(text) // 3)


def _messages_tokens(messages: List[Dict[str, Any]]) -> int:
    """Calculates the total estimated token count for a list of messages."""
    return sum(_estimate_tokens(m.get("content", "")) for m in messages)


def _format_messages_for_summary(messages: List[Dict[str, Any]]) -> str:
    """Formats a list of message dictionaries into a readable string transcript."""
    return "\n".join(
        f"{'User' if m['role'] == 'user' else 'Oracle'}: {m['content']}"
        for m in messages
    )


def summarize_messages(messages_to_summarize: List[Dict[str, Any]], existing_summary: str, llm: LLM) -> str:
    """
    Calls the LlamaIndex LLM to produce an updated summary combining the
    existing summary with newly overflowing messages.
    """
    prompt_text = _SUMMARY_PROMPT.format(
        existing_summary=existing_summary or "(none yet)",
        new_messages=_format_messages_for_summary(messages_to_summarize),
    )

    try:
        response = llm.complete(prompt_text)
        return response.text.strip()
    except Exception as e:
        print(f"Memory summarization failed: {e}")
        return existing_summary


class MemoryManager:
    """
    Manages the summary-buffer memory strategy for an active session.
    """

    def __init__(self, max_recent_tokens: int = 1200, min_recent_messages: int = 4) -> None:
        self.max_recent_tokens = max_recent_tokens
        self.min_recent_messages = min_recent_messages

    def needs_summarization(self, messages: List[Dict[str, Any]], current_summary: str) -> bool:
        """Checks if the recent messages exceed the allowed token budget."""
        recent = self._get_recent_window(messages)
        messages_tokens = _messages_tokens(recent)
        summary_tokens = _estimate_tokens(current_summary) if current_summary else 0
        
        overhead = 500 + (300 * max(1, len(recent) // 2))
        total_estimated = messages_tokens + summary_tokens + overhead
        
        return total_estimated > self.max_recent_tokens

    def _get_recent_window(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters the recent messages that fit within the token budget."""
        if len(messages) <= self.min_recent_messages:
            return messages

        recent: List[Dict[str, Any]] = []
        tokens = 0
        
        for msg in reversed(messages):
            msg_tokens = _estimate_tokens(msg.get("content", ""))
            if (tokens + msg_tokens > self.max_recent_tokens and len(recent) >= self.min_recent_messages):
                break
            recent.insert(0, msg)
            tokens += msg_tokens

        return recent

    def compress(self, session: Dict[str, Any], llm: LLM) -> Dict[str, Any]:
        """
        Compresses session memory by summarizing overflowing messages.
        Updates the session dictionary in place and returns it.
        """
        messages = session.get("messages", [])
        recent = self._get_recent_window(messages)

        to_summarize = messages[: len(messages) - len(recent)]

        if not to_summarize:
            return session

        print(f"Compressing {len(to_summarize)} messages into summary...")

        new_summary = summarize_messages(
            messages_to_summarize=to_summarize,
            existing_summary=session.get("summary", ""),
            llm=llm,
        )

        session["summary"] = new_summary
        session["messages"] = recent
        return session

    def build_agent_input(
        self,
        session: Dict[str, Any],
        base_system_prompt: str,
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Prepares the enriched system prompt and recent history tuples.
        """
        summary = session.get("summary", "")
        messages = session.get("messages", [])
        recent = self._get_recent_window(messages)

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

        history = [
            ("user" if m["role"] == "user" else "assistant", m["content"])
            for m in recent
        ]

        return enriched_prompt, history