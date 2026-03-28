"""
LLM Error Handler

Intercepts raw API exceptions from all providers and converts them into
structured, user-friendly OracleError objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_KEY = "invalid_api_key"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    CONNECTION_ERROR = "connection_error"
    CONTEXT_TOO_LONG = "context_too_long"
    CONTENT_FILTERED = "content_filtered"
    UNKNOWN = "unknown"


_USER_MESSAGES: dict[ErrorType, dict[str, str]] = {
    ErrorType.QUOTA_EXCEEDED: {
        "icon": "💸",
        "title": "Usage limit reached",
        "message": "You've used up all your available credits for this service.",
        "suggestion": "Wait for your quota to reset, or switch to another provider.",
    },
    ErrorType.INVALID_KEY: {
        "icon": "🔑",
        "title": "Invalid API key",
        "message": "The Oracle cannot authenticate with this provider.",
        "suggestion": "Check that the API key in your config is correct and valid.",
    },
    ErrorType.MODEL_UNAVAILABLE: {
        "icon": "🚫",
        "title": "Model not available",
        "message": "The selected model is temporarily unavailable or doesn't exist.",
        "suggestion": "Try selecting a different model, or come back later.",
    },
    ErrorType.RATE_LIMITED: {
        "icon": "⏳",
        "title": "Too many requests",
        "message": "The Oracle is being consulted too frequently.",
        "suggestion": "Wait a few seconds and try again.",
    },
    ErrorType.CONNECTION_ERROR: {
        "icon": "📡",
        "title": "Connection failed",
        "message": "The Oracle cannot reach the AI service right now.",
        "suggestion": "Check your internet connection. The service may be down.",
    },
    ErrorType.CONTEXT_TOO_LONG: {
        "icon": "📜",
        "title": "Conversation too long",
        "message": "The Oracle's memory is full — the conversation is too long.",
        "suggestion": "Start a new conversation by refreshing the page.",
    },
    ErrorType.CONTENT_FILTERED: {
        "icon": "🛡️",
        "title": "Message blocked by safety filter",
        "message": "The AI provider refused to process this message for safety reasons.",
        "suggestion": "Try rephrasing your question.",
    },
    ErrorType.UNKNOWN: {
        "icon": "⚡",
        "title": "Unexpected error",
        "message": "Something unexpected went wrong with the AI service.",
        "suggestion": "Try again in a moment or switch to a different provider.",
    },
}


@dataclass
class OracleError:
    """
    Structured error object containing both technical details and UI-friendly messages.
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
        return f"[{self.error_type.value}] {self.provider}/{self.model} — {self.technical_msg}"


def _classify(error: Exception, provider: str) -> ErrorType:
    """
    Inspects the exception type and message to map raw errors to an ErrorType.
    """
    msg = str(error).lower()
    cls_name = type(error).__name__.lower()

    if any(k in msg for k in
           ["invalid api key", "invalid_api_key", "incorrect api key", "authentication", "unauthorized", "401",
            "api key"]):
        return ErrorType.INVALID_KEY

    if any(k in msg for k in
           ["quota", "insufficient_quota", "billing", "exceeded your current quota", "credit", "402", "payment"]):
        return ErrorType.QUOTA_EXCEEDED

    if any(k in msg for k in
           ["rate_limit", "rate limit", "too many requests", "429", "ratelimiterror", "requests per minute",
            "tokens per minute"]):
        return ErrorType.RATE_LIMITED

    if any(k in msg for k in
           ["model not found", "no such model", "does not exist", "model_not_found", "invalid model", "404",
            "deprecated", "model is currently overloaded"]):
        return ErrorType.MODEL_UNAVAILABLE

    if any(k in msg for k in
           ["context_length", "context length", "too long", "maximum context", "token limit", "max_tokens",
            "string too long"]):
        return ErrorType.CONTEXT_TOO_LONG

    if any(k in msg for k in
           ["content filter", "safety", "policy", "blocked", "harm", "content_policy_violation", "responsible ai"]):
        return ErrorType.CONTENT_FILTERED

    if any(k in msg for k in
           ["connection", "timeout", "network", "unreachable", "service unavailable", "503", "502", "500",
            "connecterror", "connectionerror", "remotedisconnected"]):
        return ErrorType.CONNECTION_ERROR

    if "authenticationerror" in cls_name:
        return ErrorType.INVALID_KEY
    if "ratelimiterror" in cls_name:
        return ErrorType.RATE_LIMITED
    if "notfounderror" in cls_name:
        return ErrorType.MODEL_UNAVAILABLE

    return ErrorType.UNKNOWN


def handle_llm_error(error: Exception, provider: str, model: str) -> OracleError:
    """
    Converts a raw exception into a structured OracleError for UI consumption.
    """
    error_type = _classify(error, provider)

    oracle_error = OracleError(
        error_type=error_type,
        provider=provider,
        model=model,
        technical_msg=str(error),
    )

    print(f"🔴 OracleError: {oracle_error}")

    return oracle_error
