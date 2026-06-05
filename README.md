# bleo

Unofficial Python client for Brave Leo AI Chat (brave://leo-ai). No API key needed.

```bash
pip install git+https://github.com/nicolo/bleo.git
```

## CLI

```bash
bleo "tell me a joke"              # one-shot, streaming
bleo -m llama-4-scout "hello"      # specific model
bleo --no-stream "write code"      # print at once
bleo --history "my name is Alice"  # multi-turn
```

```bash
bleo                               # interactive REPL
```

Commands: `/model`, `/models`, `/history`, `/clear`, `/read`, `/quit`.

## API

```python
from bleo import Bleo

client = Bleo()
for chunk in client.stream("tell me a story"):
    print(chunk, end="", flush=True)
```

```python
client.ask("capital of Italy")  # plain
```

```python
client = Bleo(history=True)
client.ask("my name is Alice")
client.ask("what is my name?")  # → "Alice"
```

## Models

All free, no subscription required. The API accepts any model name but silently
falls back to the free tier without a Leo Premium subscription.

| Model | Maker |
|---|---|
| `automatic` | smart routing |
| `claude-haiku` | Anthropic |
| `llama-3-1-8b` | Meta |
| `llama-4-scout` | Meta |
| `llama-4-maverick` | Meta |
| `gpt-oss-20b` | OpenAI |
| `qwen-3-vl-30b` | Alibaba Cloud |

## How it works

Brave Leo uses an API at `ai-chat.bsg.brave.com/v1/conversation`. Authentication
is done via:
- `x-brave-key` header (static compile-time constant from the Brave binary)
- Optional HTTP Message Signatures (`digest` HMAC-SHA256 via pre-shared key)

Both keys are extracted from the Brave browser binary and bundled as fallbacks.
You can also provide your own via `BRAVE_X_BRAVE_KEY` and `BRAVE_PRE_SHARED_KEY`
environment variables.

## Rate limits

The free tier is rate-limited per IP (~10-15 requests burst, then ~1 req/min).
After a 429, the client waits 65s and retries. Use `--proxy` to change your IP.

## Thanks

- [cnbeining](https://www.cnbeining.com/2024/01/reverse-engineering-brave-leos-api-key-from-brave-browser/) — PSK extraction guide
