"""OriginMark - Digital signature verification for AI content."""

from originmark.core import OriginMarkClient
from originmark.cli import main

__version__ = "1.0.0"
__all__ = ["OriginMarkClient", "main", "__version__"]

# Note: OpenAI plugin imports removed - use originmark.openai_plugin_v2 directly if needed