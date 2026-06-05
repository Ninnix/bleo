from __future__ import annotations

import argparse
import sys

from . import Bleo, BleoError, __version__
from .models import list_models


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bleo",
        description="Unofficial CLI for Brave Leo AI Chat",
    )
    parser.add_argument(
        "prompt", nargs="?", default=None,
        help="One-shot prompt (positional; if omitted, starts interactive session)",
    )
    parser.add_argument(
        "-m", "--model",
        default="claude-haiku",
        help="Model name (default: claude-haiku)",
    )
    parser.add_argument(
        "--list-models", action="store_true", help="List available models"
    )
    parser.add_argument(
        "-k", "--x-brave-key",
        help="x-brave-key header value (also read from BRAVE_X_BRAVE_KEY env var)",
    )
    parser.add_argument(
        "--pre-shared-key",
        help="Pre-shared key for HTTP Message Signatures "
             "(also read from BRAVE_PRE_SHARED_KEY env var)",
    )
    parser.add_argument("--proxy", help="HTTP proxy URL")
    parser.add_argument(
        "--history", action="store_true",
        help="Enable conversation history for one-shot mode",
    )
    parser.add_argument(
        "--no-stream", action="store_true",
        help="Print entire response at once instead of streaming tokens",
    )
    parser.add_argument(
        "--version", action="store_true", help="Print version and exit"
    )
    args = parser.parse_args()

    if args.version:
        print(f"bleo {__version__}")
        return

    if args.list_models:
        for m in list_models():
            print(f"  {m}")
        return

    if args.prompt:
        _one_shot(args)
    else:
        _repl(args)


def _one_shot(args: argparse.Namespace) -> None:
    client = Bleo(
        model=args.model,
        x_brave_key=args.x_brave_key,
        pre_shared_key=args.pre_shared_key,
        proxy=args.proxy,
        history=args.history,
    )
    if args.no_stream:
        print(client.ask(args.prompt))
    else:
        for chunk in client.ask_stream(args.prompt):
            print(chunk, end="", flush=True)
        print()


def _repl(args: argparse.Namespace) -> None:
    client = Bleo(
        model=args.model,
        x_brave_key=args.x_brave_key,
        pre_shared_key=args.pre_shared_key,
        proxy=args.proxy,
        history=True,
    )
    _print_banner(args.model)
    while True:
        try:
            prompt = input("bleo> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue
        if not prompt:
            continue
        if prompt.startswith("/"):
            _handle_repl_command(client, prompt, args.model)
            continue
        try:
            for chunk in client.stream(prompt, remember=True):
                print(chunk, end="", flush=True)
        except KeyboardInterrupt:
            print("\n(interrupted)")
            continue
        except BleoError as e:
            print(f"\n  error: {e}")
            continue
        print()


def _print_banner(model: str) -> None:
    print(f"bleo {__version__} — Brave Leo AI Chat  (model: {model})")
    print("/help for commands")
    print()


def _handle_repl_command(
    client: Bleo, raw: str, current_model: str
) -> None:
    cmd = raw[1:].strip()
    rest = cmd.split(maxsplit=1)

    if not rest:
        return

    command = rest[0]
    arg = rest[1] if len(rest) > 1 else ""

    if command in ("quit", "exit", "q"):
        sys.exit(0)

    if command in ("help", "h", "?"):
        print("Commands:")
        print("  /help, /h, /?       Show this help")
        print("  /model NAME         Switch model (e.g. /model mixtral)")
        print("  /models             List available models")
        print("  /history            Show conversation history")
        print("  /clear              Clear conversation history")
        print("  /read FILE          Send file content as the next message")
        print("  /quit, /exit, /q    Exit")
        print("  Ctrl+C              Interrupt generation")
        print(f"  Current model: {client.model}")
        return

    if command == "models":
        for m in list_models():
            print(f"  {m}")
        return

    if command == "model":
        if not arg:
            print(f"Current model: {client.model}")
            return
        client.model = arg
        print(f"model set to {client.model}")
        return

    if command == "clear":
        client.reset()
        print("cleared")
        return

    if command == "history":
        if not client.history.messages:
            print("(empty)")
            return
        for m in client.history.messages:
            content = m.content
            if isinstance(content, str) and len(content) > 200:
                content = content[:200] + "..."
            print(f"  {m.role}: {content}")
        return

    if command == "read":
        if not arg:
            print("usage: /read FILE")
            return
        try:
            with open(arg) as f:
                text = f.read()
        except (FileNotFoundError, IsADirectoryError) as e:
            print(f"error: {e}")
            return
        try:
            for chunk in client.stream(text, remember=True):
                print(chunk, end="", flush=True)
        except KeyboardInterrupt:
            print("\n(interrupted)")
        print()
        return

    print(f"unknown command: /{command}")


if __name__ == "__main__":
    main()
