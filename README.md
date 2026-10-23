# bleo

<p align="center">
  <img src="logo.png" alt="Bleo logo" width="220">
</p>

Talk to Brave Leo from Python or the shell. Requires Python 3.10 or later and has no runtime dependencies. GPT-6 Luna (`bedrock-openai.gpt-5.6-luna`) is the default model.

```sh
pip install git+https://github.com/Ninnix/bleo.git
bleo "tell me a joke"          # GPT-6 Luna by default
bleo -p "tell me a joke"
bleo -m haiku "hello"          # Claude Haiku compatibility model
bleo --no-stream "write code"
bleo --models --access free
bleo --models-all
bleo --list-models --access free
bleo --refresh-models
bleo
```

The prompt has a red `🦁` banner, coloured input, streamed answers, and a model picker. Set `NO_COLOR=1` or pass `--no-color` to disable colour.

Use `/models` to pick a free model, or `/models-all` to include premium models. `/model [N|name]` switches directly. `/status`, `/history [on|off]`, `/image PATH [text]`, `/clear`, `/read FILE`, and `/quit` manage the session. Tab completes commands; arrow keys navigate history. Completed turns stay in the session. `--no-stream` prints the whole reply. A failed one-shot request exits nonzero; an interactive error leaves the prompt open.

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

`ask()`, `stream()`, and `ask_stream()` accept `model=` and `remember=` overrides. History is off by default. A user/assistant pair is saved only after a complete reply; failed or cancelled streams leave history intact. `reset()` clears history. `disable_history()` clears it and turns it off. Consume the full stream to complete a turn.

`ask_with_image(prompt, image)` accepts an HTTPS URL or image data URL. Remote images are fetched, size-checked, and inlined for Brave. If the selected model cannot read images, the request uses an available vision model.

## Models

The bundled snapshot was checked against [Brave's live catalog](https://ai-chat.bsg.brave.com/v1/models) on 2026-10-21. IDs are the names sent to the API; they may differ from the displayed model version.

```python
from bleo import list_models, model_info, refresh_models

print(list_models())          # direct chat models
print(list_models("free"))    # models available to basic users
print(list_models("premium")) # shared and premium models
print(model_info("luna"))     # name, maker, access, capabilities, encryption
refresh_models()             # explicit network call; updates this process only
```

Imports and `list_models()` work offline. Invalid refreshes keep the previous catalog. NEAR models need a different encrypted transport; summary-only models cannot chat. Both have metadata, but `list_models()` excludes them and requests reject them before sending.

| Alias or ID | Display name | Access |
| --- | --- | --- |
| `luna` / `bedrock-openai.gpt-5.6-luna` | GPT-6 Luna | Free and premium; default |
| `haiku` / `claude-3-haiku` | Claude Haiku | Compatibility ID |
| `auto` / `automatic` | Automatic routing | Compatibility ID |
| `qwen` / `qwen-14b-instruct` | Qwen 3.6 35B | Free and premium |
| `gpt-oss-20b` | GPT OSS 20B | Free and premium |
| `nemotron` | Nemotron Nano 3 30B | Free and premium |
| `qwen-3-235b` | Qwen 3.8 Flash Next | Free and premium |
| `glm` | GLM 4.7 Flash | Free and premium |
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

GPT-6 Luna is the default. It is vision-capable and available on both free and premium accounts. Claude Haiku remains a compatibility ID: it is absent from the current remote catalog, but [Brave's bundled model definitions](https://github.com/brave/brave-core/blob/master/components/ai_chat/core/browser/constants.h) specify `claude-3-haiku`. The old `claude-haiku` spelling remains an alias for that current wire ID. A live request using the corrected ID succeeds.

Brave controls routing, so the requested model may not serve the reply. `last_model` reports the server's model name, or `None` if Brave omits it. The CLI marks compatibility IDs. Retired constants and explicit IDs remain accepted for saved configurations; Brave may reject or reroute IDs it no longer advertises.

## Transport and credentials

Requests use Brave's [`/v1/chat/completions` protocol](https://github.com/brave/brave-core/blob/master/components/ai_chat/core/browser/engine/conversation_api_client.cc): OpenAI-style messages and SSE deltas. The old `/v1/conversation` endpoint returns a browser-update notice.

The standard library handles HTTP, TLS, cookies, proxies, compression, signing, and streaming. No browser or third-party package is needed. Bundled service keys are fallbacks. Explicit arguments take precedence over environment variables:

| Argument | Environment variable |
| --- | --- |
| `x_brave_key` | `BRAVE_X_BRAVE_KEY` |
| `pre_shared_key` | `BRAVE_PRE_SHARED_KEY` |
| `signing_key_id` | `BRAVE_SIGNING_KEY_ID` |
| `premium_credential` | `BRAVE_LEO_PREMIUM_CREDENTIAL` |

The signing key ID must match the pre-shared key. Changing it to match an installed browser version breaks authentication. Set `pre_shared_key=""` to disable signing. A premium credential selects Brave's premium endpoint. `proxy=` and `--proxy` accept HTTP or HTTPS proxies; standard proxy environment variables also work.

`max_retries=3` means three total attempts. Only transient failures before output are retried; authentication and other HTTP 4xx errors stop immediately. Rate limits honor `Retry-After` and JSON expiry timestamps. Longer waits than `max_retry_delay=60` raise `RatelimitError` with `retry_after` so callers can schedule another attempt. Streams stop at the first completed answer. Partial, empty, malformed, or truncated replies raise errors and are never replayed. Set `max_retries=1` to disable retries.

## Tests

```sh
python -m pip install --no-deps -e .
python -m unittest discover -s tests -v
```

Tests use only the standard library and require no service credentials. They cover signing, current payloads, model metadata and refresh validation, retries and rate limits, SSE framing and truncation, atomic conversation history, CLI failures and cleanup, and a local HTTP server for compression, cookies and transport errors. CI runs the suite on Python 3.10 and 3.13 and verifies empty runtime dependency metadata.

Thanks to [cnbeining](https://www.cnbeining.com/2024/01/reverse-engineering-brave-leos-api-key-from-brave-browser/) for the original signing-key research.
