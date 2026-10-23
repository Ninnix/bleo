# Repository map

- `src/bleo/client.py`: signed chat-completions requests, response parsing, retries and history.
- `src/bleo/_http.py`: standard-library HTTP transport and compressed streaming responses.
- `src/bleo/models.py`: model aliases, tier filtering and explicit live refresh.
- `src/bleo/models.json`: normalized Brave remote catalog snapshot; source and date are documented in README.md.
- `src/bleo/cli.py`: one-shot and interactive CLI.
- `src/bleo/ui.py`: shared banner, prompt, table, picker, line-editor and spinner helpers.
- `tests/`: offline unittest suite; transport tests start a local HTTP server.

Run `python -m pip install --no-deps -e .` followed by `python -m unittest discover -s tests -v`.

Keep GPT-6 Luna (`bedrock-openai.gpt-5.6-luna`) as the API and CLI default. Preserve the Claude Haiku compatibility ID. Preserve the matching signing key ID and PSK. A requested model can differ from the model reported by Brave; expose the latter through `last_model`. Do not commit live credentials, generated responses or local environments.
