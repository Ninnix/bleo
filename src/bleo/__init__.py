"""
bleo — Unofficial Python client for Brave Leo AI Chat (brave://leo-ai).
"""

from .client import Bleo
from .exceptions import APIError, AuthError, BleoError, RatelimitError
from .models import (
    Automatic,
    ClaudeHaiku,
    GptOss20b,
    Llama31_8b,
    Llama4Maverick,
    Llama4Scout,
    Qwen3Vl30b,
    automatic,
    claude_haiku,
    gpt_oss_20b,
    llama3_1_8b,
    llama4_maverick,
    llama4_scout,
    qwen_3_vl,
    History,
    Message,
    Role,
    list_models,
    resolve_model,
)

__version__ = "0.1.0"

__all__ = [
    "Bleo",
    "BleoError",
    "AuthError",
    "RatelimitError",
    "APIError",
    "Automatic",
    "ClaudeHaiku",
    "GptOss20b",
    "Llama31_8b",
    "Llama4Maverick",
    "Llama4Scout",
    "Qwen3Vl30b",
    "automatic",
    "claude_haiku",
    "gpt_oss_20b",
    "llama3_1_8b",
    "llama4_maverick",
    "llama4_scout",
    "qwen_3_vl",
    "History",
    "Message",
    "Role",
    "list_models",
    "resolve_model",
]

import logging
logging.getLogger("bleo").addHandler(logging.NullHandler())
