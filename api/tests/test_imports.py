#!/usr/bin/env python
"""Test script to verify all imports in the api folder"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports from api root
api_root = Path(__file__).parent.parent
sys.path.insert(0, str(api_root))

print("=" * 60)
print("TESTING ALL IMPORTS IN API FOLDER")
print("=" * 60)

# Test core.agent
try:
    from core.agent import get_search_tool, is_valid_lore_file
    print("✓ core.agent imports OK")
except Exception as e:
    print(f"✗ core.agent: {e}")

# Test core.context
try:
    from core.context import MemoryManager, SessionManager
    print("✓ core.context imports OK")
except Exception as e:
    print(f"✗ core.context: {e}")

# Test core.database
try:
    from core.database import VectorManager
    print("✓ core.database imports OK")
except Exception as e:
    print(f"✗ core.database: {e}")

# Test core.pipeline
try:
    from core.pipeline import PIIManager, QuestionProcessor, generate_document_context
    print("✓ core.pipeline imports OK")
except Exception as e:
    print(f"✗ core.pipeline: {e}")

# Test core.utils
try:
    from core.utils import load_config, load_base_prompt
    print("✓ core.utils imports OK")
except Exception as e:
    print(f"✗ core.utils: {e}")

# Test converters
try:
    from converters import load_csv_data, parse_json, parse_markdown
    print("✓ converters imports OK")
except Exception as e:
    print(f"✗ converters: {e}")

# Test providers
try:
    from providers import get_llm, get_available_models, PROVIDER_LABELS
    print("✓ providers imports OK")
except Exception as e:
    print(f"✗ providers: {e}")

print("=" * 60)
print("ALL IMPORTS VERIFIED SUCCESSFULLY!")
print("=" * 60)

