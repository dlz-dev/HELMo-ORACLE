"""
LLM Error Handler — providers/error_handler.py

Intercepts raw API exceptions from all providers and converts them into
structured, user-friendly OracleError objects.

Design philosophy:
  - The user sees a clear, human-readable message (no stack traces).
  - The developer sees the full technical detail in the console.
  - Each error has a type, a friendly title, and an actionable suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Error taxonomy
# ─────────────────────────────────────────────────────────────────────────────

class ErrorType(Enum):
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_API_KEY = "invalid_api_key"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    CONNECTION_ERROR = "connection_error"
    CONTEXT_TOO_LONG = "context_too_long"
    CONTENT_FILTERED = "content_filtered"
    OLLAMA_OFFLINE = "ollama_offline"
    UNKNOWN = "unknown"


# Maps each ErrorType to what the user sees
_USER_MESSAGES: dict[ErrorType, dict] = {
    ErrorType.QUOTA_EXCEEDED: {
        "icon": "💸",
        "title": "Usage limit reached",
        "message": "You've used up all your available credits for this service.",
        "suggestion": "Wait for your quota to reset (usually monthly), or switch to another provider in the sidebar.",
    },
    ErrorType.INVALID_API_KEY: {
        "icon": "🔑",
        "title": "Invalid API key",
        "message": "The Oracle cannot authenticate with this provider.",
        "suggestion": "Check that the API key in your config.yaml is correct and hasn't expired.",
    },
    ErrorType.MODEL_UNAVAILABLE: {
        "icon": "🚫",
        "title": "Model not available",
        "message": "The selected model is temporarily unavailable or doesn't exist.",
        "suggestion": "Try selecting a different model in the sidebar, or come back later.",
    },
    ErrorType.RATE_LIMITED: {
        "icon": "⏳",
        "title": "Too many requests",
        "message": "The Oracle is being consulted too frequently.",
        "suggestion": "Wait a few seconds and try again. If this keeps happening, consider switching to a different provider.",
    },
    ErrorType.CONNECTION_ERROR: {
        "icon": "📡",
        "title": "Connection failed",
        "message": "The Oracle cannot reach the AI service right now.",
        "suggestion": "Check your internet connection. The service may also be temporarily down.",
    },
    ErrorType.CONTEXT_TOO_LONG: {
        "icon": "📜",
        "title": "Conversation too long",
        "message": "The Oracle's memory is full — the conversation has grown too long.",
        "suggestion": "Start a new conversation by refreshing the page.",
    },
    ErrorType.CONTENT_FILTERED: {
        "icon": "🛡️",
        "title": "Message blocked by safety filter",
        "message": "The AI provider refused to process this message for safety reasons.",
        "suggestion": "Try rephrasing your question.",
    },
    ErrorType.OLLAMA_OFFLINE: {
        "icon": "🏠",
        "title": "Local AI server not running",
        "message": "Ollama doesn't seem to be running on your machine.",
        "suggestion": "Open a terminal and run: `ollama serve`. Then try again.",
    },
    ErrorType.UNKNOWN: {
        "icon": "⚡",
        "title": "Unexpected error",
        "message": "Something unexpected went wrong with the AI service.",
        "suggestion": "Try again in a moment. If the problem persists, try switching to a different provider.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# OracleError — the structured error object
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OracleError:
    """
    Structured error ready for display in Streamlit.

    Attributes:
        error_type:     Enum category of the error.
        provider:       Which provider caused the error (e.g. "groq").
        model:          Which model was being used.
        technical_msg:  Raw exception message (for logs / expander).
        icon:           Emoji for the UI.
        title:          Short human-readable title.
        message:        Plain-English explanation for the user.
        suggestion:     Actionable next step for the user.
    """
    error_type: ErrorType
    provider: str
    model: str
    technical_msg: str

    @property
    def icon(self) -> str:
        return _USER_MESSAGES[self.error_type]["icon"]

    @property
    def title(self) -> str:
        return _USER_MESSAGES[self.error_type]["title"]

    @property
    def message(self) -> str:
        return _USER_MESSAGES[self.error_type]["message"]

    @property
    def suggestion(self) -> str:
        return _USER_MESSAGES[self.error_type]["suggestion"]

    def __str__(self) -> str:
        return (
            f"[{self.error_type.value}] {self.provider}/{self.model} — {self.technical_msg}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Classification logic — maps raw exceptions → ErrorType
# ─────────────────────────────────────────────────────────────────────────────

def _classify(error: Exception, provider: str) -> ErrorType:
    """
    Inspects the exception type and message to determine the ErrorType.
    Covers Groq, OpenAI, Anthropic, Google Gemini, and Ollama.
    """
    msg = str(error).lower()
    cls = type(error).__name__

    # ── Ollama (local) ────────────────────────────────────────────
    if provider == "ollama":
        if any(k in msg for k in ["connection refused", "connect call failed", "cannot connect"]):
            return ErrorType.OLLAMA_OFFLINE
        if "not found" in msg or "no such model" in msg:
            return ErrorType.MODEL_UNAVAILABLE

    # ── API key issues ────────────────────────────────────────────
    if any(k in msg for k in [
        "invalid api key", "invalid_api_key", "incorrect api key",
        "authentication", "unauthorized", "401", "api key",
    ]):
        return ErrorType.INVALID_API_KEY

    # ── Quota / billing ───────────────────────────────────────────
    if any(k in msg for k in [
        "quota", "insufficient_quota", "billing", "exceeded your current quota",
        "rate limit exceeded", "tokens per", "credit", "402", "payment",
    ]):
        # Distinguish hard quota (billing) from soft rate limit (speed)
        if any(k in msg for k in ["billing", "credit", "quota", "402", "payment", "insufficient"]):
            return ErrorType.QUOTA_EXCEEDED
        return ErrorType.RATE_LIMITED

    # ── Rate limiting (too fast) ──────────────────────────────────
    if any(k in msg for k in [
        "rate_limit", "rate limit", "too many requests", "429",
        "ratelimiterror", "requests per minute", "tokens per minute",
    ]):
        return ErrorType.RATE_LIMITED

    # ── Model not found / unavailable ─────────────────────────────
    if any(k in msg for k in [
        "model not found", "no such model", "does not exist",
        "model_not_found", "invalid model", "404", "deprecated",
        "model is currently overloaded",
    ]):
        return ErrorType.MODEL_UNAVAILABLE

    # ── Context / token length ────────────────────────────────────
    if any(k in msg for k in [
        "context_length", "context length", "too long", "maximum context",
        "token limit", "max_tokens", "string too long",
    ]):
        return ErrorType.CONTEXT_TOO_LONG

    # ── Content safety filters ────────────────────────────────────
    if any(k in msg for k in [
        "content filter", "safety", "policy", "blocked", "harm",
        "content_policy_violation", "responsible ai",
    ]):
        return ErrorType.CONTENT_FILTERED

    # ── Network / connectivity ────────────────────────────────────
    if any(k in msg for k in [
        "connection", "timeout", "network", "unreachable",
        "service unavailable", "503", "502", "500",
        "connecterror", "connectionerror", "remotedisconnected",
    ]):
        return ErrorType.CONNECTION_ERROR

    # ── Exception class name fallback ─────────────────────────────
    if "authenticationerror" in cls.lower():
        return ErrorType.INVALID_API_KEY
    if "ratelimiterror" in cls.lower():
        return ErrorType.RATE_LIMITED
    if "notfounderror" in cls.lower():
        return ErrorType.MODEL_UNAVAILABLE

    return ErrorType.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def handle_llm_error(error: Exception, provider: str, model: str) -> OracleError:
    """
    Main entry point. Takes a raw exception and returns a structured OracleError.

    Usage:
        except Exception as e:
            oracle_error = handle_llm_error(e, provider="groq", model="llama-3.3-70b")
            display_error(oracle_error)
    """
    error_type = _classify(error, provider)

    oracle_error = OracleError(
        error_type=error_type,
        provider=provider,
        model=model,
        technical_msg=str(error),
    )

    # Always log the full technical detail to console (for developers)
    print(f"🔴 OracleError: {oracle_error}")

    return oracle_error
