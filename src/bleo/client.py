from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import random
import time
from typing import Any, Dict, Iterator, List, Optional, Union

import httpx

from .exceptions import APIError, AuthError, BleoError, RatelimitError
from .models import (
    ClaudeHaiku,
    History,
    Message,
    Role,
    resolve_model,
)

log = logging.getLogger("bleo")

_BASE = "https://ai-chat.bsg.brave.com"
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)

_CONVERSATION = "/v1/conversation"

_DEFAULT_MODEL = ClaudeHaiku

_KNOWN_X_BRAVE_KEY = "qztbjzBqJueQZLFkwTTJrieu8Vw3789u"
_KNOWN_PRE_SHARED_KEY = "a1a5e78387143d981cc13d52445983b7b9884c2a46009122710b675dfe11e280"


def _make_digest(body: str) -> str:
    sha256 = hashlib.sha256(body.encode("utf-8")).digest()
    return base64.b64encode(sha256).decode("ascii")


def _make_hmac_signature(body: str, psk: str) -> str:
    digest_val = _make_digest(body)
    signing_input = f"digest: SHA-256={digest_val}"
    sig = hmac.new(
        psk.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(sig).decode("ascii")


def _make_key_id() -> str:
    return "linux-148-release"


class Bleo:
    """Client for Brave Leo AI Chat (brave://leo-ai).

    Auth uses ``x-brave-key`` header + optional HTTP Message Signatures
    (``digest`` HMAC-SHA256 via ``pre_shared_key``).  The key and PSK
    are compile-time constants in the Brave binary.

    Keys can be provided via constructor args or environment variables:
    ``BRAVE_X_BRAVE_KEY`` and ``BRAVE_PRE_SHARED_KEY``.

    Known defaults are bundled as fallback.

    Args:
        model: Model alias or full model id (default: claude-3-haiku).
        x_brave_key: The x-brave-key header value.
        pre_shared_key: Pre-shared key for HMAC-SHA256 signing.
        timeout: HTTP timeout in seconds (default: 60).
        max_retries: Number of retries on transient errors (default: 3).
        history: Enable multi-turn memory (default: False).
        proxy: Optional proxy URL.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        *,
        x_brave_key: Optional[str] = None,
        pre_shared_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        history: bool = False,
        proxy: Optional[str] = None,
    ):
        self.model = resolve_model(model)
        self.x_brave_key = (
            x_brave_key
            or os.environ.get("BRAVE_X_BRAVE_KEY")
            or _KNOWN_X_BRAVE_KEY
        )
        self.pre_shared_key = pre_shared_key or os.environ.get(
            "BRAVE_PRE_SHARED_KEY"
        ) or _KNOWN_PRE_SHARED_KEY
        self.timeout = timeout
        self.max_retries = max(1, int(max_retries))
        self.proxy = proxy
        self.history_enabled = bool(history)
        self.history = History(model=self.model)

        client_kwargs: Dict[str, Any] = {
            "http2": False,
            "timeout": httpx.Timeout(timeout, connect=15.0, read=timeout),
            "follow_redirects": True,
        }
        if proxy:
            client_kwargs["proxies"] = proxy

        self._client = httpx.Client(**client_kwargs)

    def __enter__(self) -> "Bleo":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def reset(self) -> None:
        self.history.clear()

    def enable_history(self) -> None:
        self.history_enabled = True

    def disable_history(self) -> None:
        self.history_enabled = False
        self.history.clear()

    def _headers(
        self,
        body: str,
        *,
        stream: bool = True,
    ) -> Dict[str, str]:
        hdrs: Dict[str, str] = {
            "User-Agent": _UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Content-Type": "application/json",
            "x-brave-key": self.x_brave_key,
            "braveservicekey": self.x_brave_key,
        }
        if stream:
            hdrs["Accept"] = "text/event-stream"
        if self.pre_shared_key:
            digest_val = _make_digest(body)
            hdrs["digest"] = f"SHA-256={digest_val}"
            sig = _make_hmac_signature(body, self.pre_shared_key)
            key_id = _make_key_id()
            hdrs["Authorization"] = (
                f'Signature keyId="{key_id}",algorithm="hs2019",'
                f'headers="digest",signature="{sig}"'
            )
        return hdrs

    def _build_payload(
        self,
        events: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        stream: bool = True,
    ) -> Dict[str, Any]:
        return {
            "capability": "chat",
            "events": events,
            "model": resolve_model(model or self.model),
            "stream": stream,
            "system_language": "en_US",
            "use_citations": True,
        }

    def _chat_stream(
        self,
        payload: Dict[str, Any],
    ):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return self._client.stream(
            "POST",
            f"{_BASE}{_CONVERSATION}",
            content=body,
            headers=self._headers(body),
        )

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        try:
            resp.read()
            body = resp.text
        except Exception:
            body = ""
        if resp.status_code == 401 or resp.status_code == 403:
            raise AuthError(f"auth failed: {body[:200]}")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = None
            raise RatelimitError(body, retry_after=retry_after)
        raise APIError(
            f"chat failed: HTTP {resp.status_code}", resp.status_code, body
        )

    @staticmethod
    def _iter_sse(resp: httpx.Response) -> Iterator[str]:
        for raw in resp.iter_lines():
            if not raw:
                continue
            if not raw.startswith("data:"):
                continue
            data = raw[5:].lstrip()
            if data:
                yield data

    def _attempt_stream(
        self,
        payload: Dict[str, Any],
    ) -> Iterator[str]:
        with self._chat_stream(payload) as resp:
            if resp.status_code != 200:
                self._raise_for_status(resp)
            saw_any = False
            for data in self._iter_sse(resp):
                if data == "[DONE]":
                    return
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                chunk = self._extract_chunk(obj)
                if chunk:
                    saw_any = True
                    yield chunk
            if not saw_any:
                raise APIError("empty stream", 200, "")

    @staticmethod
    def _extract_chunk(obj: dict) -> Optional[str]:
        typ = obj.get("type", "")
        if typ == "completion":
            return obj.get("completion")
        if typ == "conversationTitle":
            return None
        return None

    def _stream_with_retry(
        self,
        payload: Dict[str, Any],
    ) -> Iterator[str]:
        last_exc: Optional[BaseException] = None
        for attempt in range(self.max_retries):
            yielded = False
            try:
                yield from self._attempt_stream(payload)
                return
            except (httpx.RemoteProtocolError, httpx.ReadError) as e:
                if yielded:
                    raise
                last_exc = e
            except APIError as e:
                if e.status_code and e.status_code >= 500:
                    if yielded:
                        raise
                    last_exc = e
                else:
                    raise
            except RatelimitError as e:
                if yielded:
                    raise
                delay = getattr(e, "retry_after", None)
                if not delay or delay < 1:
                    delay = 65
                log.warning("rate limited, retrying in %ds", delay)
                time.sleep(delay)
                last_exc = e
                continue
            except httpx.TimeoutException as e:
                if yielded:
                    raise
                last_exc = e
            if attempt < self.max_retries - 1:
                delay = 1.5 * (2**attempt) + random.uniform(0, 0.25)
                time.sleep(delay)
        if last_exc is not None:
            raise last_exc
        raise BleoError("exhausted retries with no specific error")

    def _to_events(self, messages: List[dict]) -> List[dict]:
        events = []
        for m in messages:
            events.append({
                "content": m.get("content", ""),
                "role": m.get("role", "user"),
                "type": "chatMessage",
            })
        return events

    def stream(
        self,
        prompt: Union[str, List[Union[str, dict]]],
        *,
        remember: Optional[bool] = None,
        model: Optional[str] = None,
    ) -> Iterator[str]:
        if remember is None:
            remember = self.history_enabled
        if remember:
            self.history.add_user(prompt)
            messages = self.history.to_messages()
        else:
            messages = [Message(role=Role.User, content=prompt).to_dict()]

        events = self._to_events(messages)
        payload = self._build_payload(
            events,
            model=model or self.model,
        )
        return self._stream_with_retry(payload)

    def ask(
        self,
        prompt: Union[str, List[Union[str, dict]]],
        *,
        remember: Optional[bool] = None,
        model: Optional[str] = None,
    ) -> str:
        collected: List[str] = []
        for chunk in self.stream(prompt, remember=remember, model=model):
            collected.append(chunk)
        result = "".join(collected)
        if self.history_enabled and (remember is None or remember):
            self.history.add_assistant(result)
        return result

    def ask_stream(
        self,
        prompt: Union[str, List[Union[str, dict]]],
        *,
        remember: Optional[bool] = None,
        model: Optional[str] = None,
    ) -> Iterator[str]:
        collected: List[str] = []
        for chunk in self.stream(prompt, remember=remember, model=model):
            collected.append(chunk)
            yield chunk
        result = "".join(collected)
        if self.history_enabled and (remember is None or remember):
            self.history.add_assistant(result)
