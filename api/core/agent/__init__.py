"""
Agent module for Oracle - handles tool creation and content validation.
"""

from .guardian import is_valid_lore_file
from .tools_oracle import get_search_tool

__all__ = [
    "is_valid_lore_file",
    "get_search_tool",
]

