from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

# --- Brave Leo Models (/v1/conversation API) ---
#
# Only free models are verified to respond as themselves.
# Premium model names (claude-sonnet, claude-opus, gpt-oss-120b,
# qwen-3-235b, qwen-3-coder-480b, deepseek-v3-1, mistral-large,
# pixtral-large) are accepted by the API but silently fall back
# to Qwen 3.5 30B without a paid Leo Premium subscription.

ClaudeHaiku = "claude-haiku"
Llama31_8b = "llama-3-1-8b"
Llama4Scout = "llama-4-scout"
Llama4Maverick = "llama-4-maverick"
GptOss20b = "gpt-oss-20b"
Qwen3Vl30b = "qwen-3-vl-30b"
Automatic = "automatic"

claude_haiku = ClaudeHaiku
llama3_1_8b = Llama31_8b
llama4_scout = Llama4Scout
llama4_maverick = Llama4Maverick
gpt_oss_20b = GptOss20b
qwen_3_vl = Qwen3Vl30b
automatic = Automatic

MODEL_ALIASES: Dict[str, str] = {
    "auto": Automatic,
    "automatic": Automatic,
    "claude": ClaudeHaiku,
    "claude-haiku": ClaudeHaiku,
    "claude_haiku": ClaudeHaiku,
    "haiku": ClaudeHaiku,
    "claude-3-haiku": ClaudeHaiku,
    "llama": Llama31_8b,
    "llama-3": Llama31_8b,
    "llama-3-1": Llama31_8b,
    "llama-3-1-8b": Llama31_8b,
    "llama3": Llama31_8b,
    "llama-3-8b": Llama31_8b,
    "llama3-8b": Llama31_8b,
    "llama-3-70b": Llama31_8b,
    "llama3-70b": Llama31_8b,
    "llama4": Llama4Scout,
    "llama-4": Llama4Scout,
    "llama-4-scout": Llama4Scout,
    "llama-4-maverick": Llama4Maverick,
    "llama4-scout": Llama4Scout,
    "llama4-maverick": Llama4Maverick,
    "maverick": Llama4Maverick,
    "scout": Llama4Scout,
    "gpt-oss": GptOss20b,
    "gpt_oss": GptOss20b,
    "gpt-oss-20b": GptOss20b,
    "gpt_oss_20b": GptOss20b,
    "qwen": Qwen3Vl30b,
    "qwen-3": Qwen3Vl30b,
    "qwen-3-vl": Qwen3Vl30b,
    "qwen-3-vl-30b": Qwen3Vl30b,
    "qwen_3_vl": Qwen3Vl30b,
    "qwen-vl-30b": Qwen3Vl30b,
    "qwen_vl": Qwen3Vl30b,
}


def resolve_model(name: Optional[str]) -> str:
    if not name:
        return ClaudeHaiku
    return MODEL_ALIASES.get(name.strip().lower(), name.strip())


def list_models() -> List[str]:
    return [
        Automatic, ClaudeHaiku, Llama31_8b,
        Llama4Scout, Llama4Maverick,
        GptOss20b, Qwen3Vl30b,
    ]


class Role:
    User = "user"
    Assistant = "assistant"
    System = "system"


Content = Union[str, List[Union[str, dict]]]


@dataclass
class Message:
    role: str
    content: Content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class History:
    model: str = ClaudeHaiku
    messages: List[Message] = field(default_factory=list)

    def add_user(self, content: Content) -> None:
        self.messages.append(Message(role=Role.User, content=content))

    def add_assistant(self, content: str) -> None:
        self.messages.append(Message(role=Role.Assistant, content=content))

    def to_messages(self) -> List[dict]:
        return [m.to_dict() for m in self.messages]

    def clear(self) -> None:
        self.messages.clear()
