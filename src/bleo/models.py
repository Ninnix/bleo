from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from ._http import Session
from .exceptions import APIError

ClaudeHaiku = "claude-3-haiku"
ClaudeSonnet = "claude-3-sonnet"
ClaudeOpus = "claude-opus"
GptLuna = "bedrock-openai.gpt-5.6-luna"
GptTerra = "bedrock-openai.gpt-5.6-terra"
DefaultModel = GptLuna
GptOss120b = "gpt-oss-120b"
Qwen36 = "qwen-14b-instruct"
Qwen38 = "qwen-3-235b"
Glm47Flash = "glm-4-7-flash"
Glm53 = "glm-5-3"
Grok = "bedrock-xai.grok-4.3"
Kimi = "kimi-k2-5"
Deepseek = "deepseek-v3-2"
Nemotron = "nemotron-nano-3-30b"
MistralLarge = "mistral-large"

# Retain the original constants for callers with saved configurations.
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
    "qwen": Qwen36,
    "qwen-3": Qwen3Vl30b,
    "qwen-3-vl": Qwen3Vl30b,
    "qwen-3-vl-30b": Qwen3Vl30b,
    "qwen_3_vl": Qwen3Vl30b,
    "qwen-vl-30b": Qwen3Vl30b,
    "qwen_vl": Qwen3Vl30b,
    "sonnet": ClaudeSonnet,
    "claude-sonnet": ClaudeSonnet,
    "opus": ClaudeOpus,
    "luna": GptLuna,
    "gpt-luna": GptLuna,
    "gpt-6-luna": GptLuna,
    "terra": GptTerra,
    "gpt-oss-120b": GptOss120b,
    "qwen-3.6": Qwen36,
    "qwen-3.8": Qwen38,
    "glm": Glm47Flash,
    "glm5": Glm53,
    "grok": Grok,
    "kimi": Kimi,
    "deepseek": Deepseek,
    "nemotron": Nemotron,
    "mistral": MistralLarge,
}

_CATALOG_URL = "https://ai-chat.bsg.brave.com/v1/models"
_FALLBACKS = [
    {"id": ClaudeHaiku, "name": "Claude Haiku", "maker": "Anthropic",
     "access": "basic_and_premium", "capabilities": ["chat"],
     "encrypted": False, "advertised": False},
    {"id": Automatic, "name": "Automatic", "maker": "Brave",
     "access": "basic_and_premium", "capabilities": ["chat"],
     "encrypted": False, "advertised": False},
]
_MODELS = {item["id"]: item for item in _FALLBACKS}
for _item in json.loads(Path(__file__).with_name("models.json").read_text(encoding="utf-8")):
    _MODELS[_item["id"]] = {**_item, "advertised": True}


def resolve_model(name: Optional[str]) -> str:
    if not name or not name.strip():
        return DefaultModel
    return MODEL_ALIASES.get(name.strip().lower(), name.strip())


def model_info(name: str) -> Optional[dict]:
    """Return independent metadata, including whether Brave advertises this model."""
    return deepcopy(_MODELS.get(resolve_model(name)))


def list_models(access: Optional[str] = None) -> List[str]:
    """List direct chat models; premium includes models shared with the free tier."""
    if access not in (None, "free", "premium"):
        raise ValueError("access must be free or premium")
    return [name for name, item in _MODELS.items()
            if "chat" in item["capabilities"] and not item["encrypted"]
            and (access != "free" or item["access"] in ("basic", "basic_and_premium"))]


def refresh_models(*, timeout: float = 30) -> List[str]:
    """Refresh this process's catalog. Imports and list_models() remain offline."""
    global _MODELS
    session = Session(timeout=timeout)
    try:
        response = session.get(_CATALOG_URL)
        if response.status_code != 200:
            raise APIError("Could not fetch Brave model catalog", response.status_code)
        entries = json.loads(response.text)
        if not isinstance(entries, list) or not entries:
            raise ValueError("Expected a nonempty model list")
        models = {item["id"]: deepcopy(item) for item in _FALLBACKS}
        seen = set()
        for entry in entries:
            options = entry["options"]
            name = options["name"]
            capabilities = entry["capabilities"]
            access = options["access"]
            encrypted = entry.get("is_near_model", False)
            if (not isinstance(name, str) or not name or name in seen
                    or not isinstance(capabilities, list)
                    or not all(isinstance(value, str) for value in capabilities)
                    or access not in ("basic", "premium", "basic_and_premium")
                    or not isinstance(encrypted, bool)
                    or not isinstance(entry["display_name"], str)
                    or not isinstance(options["display_maker"], str)):
                raise ValueError("Invalid model metadata")
            seen.add(name)
            models[name] = {"id": name, "name": entry["display_name"],
                            "maker": options["display_maker"], "access": access,
                            "capabilities": capabilities, "encrypted": encrypted,
                            "advertised": True}
    except (ValueError, KeyError, TypeError) as error:
        raise APIError("Invalid Brave model catalog") from error
    finally:
        session.close()
    _MODELS = models
    return list_models()


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
    model: str = DefaultModel
    messages: List[Message] = field(default_factory=list)

    def add_user(self, content: Content) -> None:
        self.messages.append(Message(role=Role.User, content=content))

    def add_assistant(self, content: str) -> None:
        self.messages.append(Message(role=Role.Assistant, content=content))

    def to_messages(self) -> List[dict]:
        return [m.to_dict() for m in self.messages]

    def clear(self) -> None:
        self.messages.clear()
