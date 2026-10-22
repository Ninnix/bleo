# bleo

<p align="center">
  <img src="logo.png" alt="Bleo logo" width="220">
</p>

Unofficial Python client for Brave Leo, using Python 3.10+ with **zero runtime dependencies**. Haiku (`claude-3-haiku`) is the default requested model in the API and CLI.

```sh
pip install git+https://github.com/Ninnix/bleo.git
bleo "tell me a joke"
bleo -m luna "hello"
bleo --no-stream "write code"
bleo --list-models --access free
bleo --refresh-models
bleo
```

Interactive commands: `/model NAME`, `/models`, `/history`, `/clear`, `/read FILE`, `/quit`. The interactive session remembers completed turns. `--no-stream` prints complete replies. Request failures return a nonzero exit status; interactive errors leave the session open.

## Python API

```python
from bleo import Bleo

with Bleo(history=True) as client:
    print(client.ask("My name is Alice."))
    for chunk in client.stream("What is my name?"):
        print(chunk, end="", flush=True)
    print()
    print("Requested:", client.model, "Served:", client.last_model)
```

`ask()`, `stream()` and `ask_stream()` accept `model=` and `remember=` overrides. History is off by default. All three methods record a user/assistant pair only after a successful complete reply. Failed or cancelled streams leave history intact. `reset()` clears it; `disable_history()` clears it and turns it off. Consume the whole stream to complete a turn.

`ask_with_image(prompt, image)` accepts an HTTPS image URL or image data URL. If the selected model is text-only, it selects an available vision-capable model for that request.

## Models

The bundled snapshot comes from [Brave's live catalog](https://ai-chat.bsg.brave.com/v1/models), checked on 2026-10-21. IDs are the API's wire names: their spelling can differ from the displayed model version.

```python
from bleo import list_models, model_info, refresh_models

print(list_models())          # direct chat models
print(list_models("free"))    # models available to basic users
print(list_models("premium")) # shared and premium models
print(model_info("luna"))     # name, maker, access, capabilities, encryption
refresh_models()             # explicit network call; updates this process only
```

Imports and `list_models()` work offline. Invalid refreshes preserve the previous catalog. NEAR models require a different encrypted transport and summary-only models cannot serve chat; both have metadata but are excluded from `list_models()` and rejected before requests.

| Alias or ID | Display name | Access |
| --- | --- | --- |
| `haiku` / `claude-3-haiku` | Claude Haiku | Compatibility ID; default |
| `auto` / `automatic` | Automatic routing | Compatibility ID |
| `qwen` / `qwen-14b-instruct` | Qwen 3.6 35B | Free and premium |
| `gpt-oss-20b` | GPT OSS 20B | Free and premium |
| `nemotron` | Nemotron Nano 3 30B | Free and premium |
| `qwen-3-235b` | Qwen 3.8 Flash Next | Free and premium |
| `glm` | GLM 4.7 Flash | Free and premium |
| `luna` | GPT-6 Luna | Free and premium |
| `maverick` | Llama 4 Maverick | Free and premium |
| `automatic-bravebot` | Automatic bot routing | Free and premium |
| `sonnet` | Claude 5.5 Sonnet | Premium |
| `opus` | Claude Opus 5.5 | Premium |
| `gpt-oss-120b` | GPT OSS 120B | Premium |
| `bedrock-openai.gpt-5.5` | GPT-5.5 (Bedrock) | Premium |
| `terra` / `bedrock-openai.gpt-5.4` | GPT 5.6 Terra | Premium |
| `grok` | Grok 4.7 | Premium |
| `mistral` | Mistral Large | Premium |
| `qwen-3-235b-bedrock` | Qwen 3 235B | Premium |
| `deepseek` | Deepseek V3.2 | Premium |
| `kimi` | Kimi K2.5 | Premium |
| `glm5` | GLM 5.3 | Premium |

Haiku is the default. It is absent from the current remote catalog, but [Brave's bundled model definitions](https://github.com/brave/brave-core/blob/master/components/ai_chat/core/browser/constants.h) specify `claude-3-haiku`. The old `claude-haiku` spelling remains an alias for that current wire ID. A live request using the corrected ID succeeds.

The service controls routing; selecting a model does not guarantee that model serves the response. `last_model` exposes the server-reported identity, or `None` when it is missing or blank. The CLI labels compatibility IDs separately. Retired constants and explicit IDs remain accepted for saved configurations; unadvertised IDs may be rejected or rerouted by Brave.

## Transport and credentials

Requests use Brave's current [`/v1/chat/completions` protocol](https://github.com/brave/brave-core/blob/master/components/ai_chat/core/browser/engine/conversation_api_client.cc), including OpenAI-style messages and SSE deltas. The retired `/v1/conversation` endpoint returns a browser-update notice.

Python's standard library handles HTTP, TLS, cookies, proxies, gzip/deflate, signing and streaming. No browser or third-party Python package is required. Bundled service keys are fallbacks; explicit arguments override environment variables:

| Argument | Environment variable |
| --- | --- |
| `x_brave_key` | `BRAVE_X_BRAVE_KEY` |
| `pre_shared_key` | `BRAVE_PRE_SHARED_KEY` |
| `signing_key_id` | `BRAVE_SIGNING_KEY_ID` |
| `premium_credential` | `BRAVE_LEO_PREMIUM_CREDENTIAL` |

The signing key ID must match the supplied pre-shared key; changing it to match an installed browser version breaks authentication. Set `pre_shared_key=""` to disable signing. A premium credential selects Brave's premium endpoint. `proxy=` / `--proxy` supports HTTP and HTTPS proxies; standard proxy environment variables also work.

`max_retries=3` counts total attempts. Only transient failures before any text is emitted are retried. Authentication and other HTTP 4xx errors are terminal. Rate limits honor numeric/date `Retry-After` and JSON expiry timestamps. Delays above `max_retry_delay=60` seconds are returned as `RatelimitError` with `retry_after` for callers to schedule. Streaming ends at the first completed answer, ignoring continuation turns that Brave may append afterward. Partial, empty, malformed or truncated completions raise errors; partial output is never replayed automatically. Use `max_retries=1` to disable retries.

## Tests

```sh
python -m pip install --no-deps -e .
python -m unittest discover -s tests -v
```

Tests use only the standard library and require no service credentials. They cover signing, current payloads, model metadata and refresh validation, retries and rate limits, SSE framing and truncation, atomic conversation history, CLI failures and cleanup, and a local HTTP server for compression, cookies and transport errors. CI runs the suite on Python 3.10 and 3.13 and verifies empty runtime dependency metadata.

Thanks to [cnbeining](https://www.cnbeining.com/2024/01/reverse-engineering-brave-leos-api-key-from-brave-browser/) for the original signing-key research.
