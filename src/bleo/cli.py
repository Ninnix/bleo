from __future__ import annotations

import argparse
from http.client import HTTPException
from pathlib import Path
import sys

from . import Bleo, BleoError, __version__
from .models import ClaudeHaiku, list_models, model_info, refresh_models, resolve_model


def main() -> None:
    parser = argparse.ArgumentParser(prog="bleo", description="Brave Leo AI Chat")
    parser.add_argument("prompt", nargs="?", help="Prompt; omit for interactive chat")
    parser.add_argument("-m", "--model", default=ClaudeHaiku,
                        help=f"Model name or alias (default: {ClaudeHaiku})")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--refresh-models", action="store_true",
                        help="Fetch and print Brave's current model catalog")
    parser.add_argument("--access", choices=("free", "premium"), help="Filter model list")
    parser.add_argument("-k", "--x-brave-key", help="Also BRAVE_X_BRAVE_KEY")
    parser.add_argument("--pre-shared-key", help="Also BRAVE_PRE_SHARED_KEY")
    parser.add_argument("--signing-key-id", help="Also BRAVE_SIGNING_KEY_ID")
    parser.add_argument("--proxy", help="HTTP or HTTPS proxy URL")
    parser.add_argument("--history", action="store_true", help="Remember conversation turns")
    parser.add_argument("--no-stream", action="store_true", help="Print the complete reply")
    parser.add_argument("--version", action="version", version=f"bleo {__version__}")
    args = parser.parse_args()
    try:
        if args.refresh_models:
            refresh_models()
        if args.list_models or args.refresh_models:
            _print_models(args.access)
            return
        with Bleo(model=args.model, x_brave_key=args.x_brave_key,
                  pre_shared_key=args.pre_shared_key, signing_key_id=args.signing_key_id,
                  proxy=args.proxy, history=args.history or args.prompt is None) as client:
            if args.prompt is not None:
                _print_reply(client, args.prompt, args.no_stream)
            else:
                _repl(client, args.no_stream)
    except (BleoError, OSError, HTTPException, ValueError) as error:
        print(f"bleo: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        print(file=sys.stderr)
        raise SystemExit(130) from None


def _print_models(access=None):
    for name in list_models(access):
        info = model_info(name)
        tier = "premium" if info["access"] == "premium" else "free"
        note = "; compatibility ID" if not info["advertised"] else ""
        print(f"{name}\t{info['name']} ({tier}{note})")


def _print_reply(client, prompt, no_stream=False):
    if no_stream:
        print(client.ask(prompt))
    else:
        for chunk in client.stream(prompt):
            print(chunk, end="", flush=True)
        print()


def _repl(client, no_stream=False):
    print(f"bleo {__version__} — Brave Leo AI Chat (model: {client.model})")
    print("/help for commands\n")
    while True:
        try:
            prompt = input("bleo> ").strip()
            if not prompt:
                continue
            if prompt.startswith("/"):
                if not _handle_repl_command(client, prompt, no_stream):
                    return
            else:
                _print_reply(client, prompt, no_stream)
        except EOFError:
            print()
            return
        except KeyboardInterrupt:
            print("\n(interrupted)")
        except (BleoError, OSError, HTTPException, UnicodeError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)


def _handle_repl_command(client, raw, no_stream=False):
    parts = raw[1:].strip().split(maxsplit=1)
    if not parts:
        return True
    command = parts[0]
    arg = parts[1] if len(parts) > 1 else ""
    if command in ("quit", "exit", "q"):
        return False
    if command in ("help", "h", "?"):
        print("/model NAME, /models, /history, /clear, /read FILE, /quit")
        print(f"Current model: {client.model}")
    elif command == "models":
        _print_models()
    elif command == "model":
        if arg:
            client.model = resolve_model(arg)
            client.history.model = client.model
        print(f"Current model: {client.model}")
    elif command == "clear":
        client.reset()
        print("cleared")
    elif command == "history":
        if not client.history.messages:
            print("(empty)")
        for message in client.history.messages:
            print(f"{message.role}: {str(message.content)[:200]}")
    elif command == "read":
        if not arg:
            print("usage: /read FILE")
        else:
            _print_reply(client, Path(arg).read_text(encoding="utf-8"), no_stream)
    else:
        print(f"unknown command: /{command}")
    return True


if __name__ == "__main__":
    main()
