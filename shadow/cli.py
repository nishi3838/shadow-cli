"""shadow REPL — entry point."""

import os
import sys
import traceback
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from . import config as cfg_module
from .gateway import GatewayClient
from .conversation import Conversation

_console = Console()

HISTORY_FILE = Path.home() / ".shadow" / "history"
BANNER = "[bold cyan]shadow[/bold cyan] — AI coding assistant\nType [bold]/help[/bold] for commands, [bold]/exit[/bold] or Ctrl-D to quit.\n"

HELP_TEXT = """\
**Commands**
- `/exit` or Ctrl-D — quit
- `/clear` — clear conversation history (start fresh)
- `/model` — show current model
- `/cwd` — show working directory
- `/help` — this message
"""


def _make_keybindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("escape", "enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    return kb


def _stream_print(chunk: str, buf: list[str]) -> None:
    buf.append(chunk)
    _console.print(chunk, end="", markup=False, highlight=False)


def main() -> None:
    cwd = os.getcwd()

    _console.print(BANNER)

    cfg = cfg_module.ensure()
    client = GatewayClient(cfg)
    conv = Conversation(cwd)

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        key_bindings=_make_keybindings(),
        multiline=False,
    )

    _console.print(
        f"[dim]model:[/dim] {cfg['model']}  "
        f"[dim]cwd:[/dim] {cwd}\n"
    )

    while True:
        try:
            user_input = session.prompt("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            _console.print("\n[dim]Bye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            _handle_command(user_input, conv, cfg)
            continue

        conv.add_user(user_input)

        _console.print()
        _console.print("[bold cyan]shadow>[/bold cyan] ", end="")

        text_buf: list[str] = []

        try:
            updated = client.run_turn(
                conv.messages,
                conv.system_prompt(),
                on_text=lambda chunk: _stream_print(chunk, text_buf),
            )
        except Exception as exc:
            _console.print(f"\n[red]Error:[/red] {exc}")
            _console.print(traceback.format_exc(), markup=False)
            conv.messages.pop()
            continue

        _console.print()

        full_text = "".join(text_buf)
        if full_text and _looks_like_markdown(full_text):
            _console.print(Rule(style="dim"))
            _console.print(Markdown(full_text))

        conv.replace_last_messages(updated)
        _console.print()


def _handle_command(cmd: str, conv: Conversation, cfg: dict) -> None:
    cmd = cmd.lower().strip()
    if cmd in ("/exit", "/quit"):
        _console.print("[dim]Bye.[/dim]")
        sys.exit(0)
    elif cmd == "/clear":
        conv.messages.clear()
        _console.print("[green]Conversation cleared.[/green]")
    elif cmd == "/model":
        _console.print(f"[cyan]{cfg['model']}[/cyan]")
    elif cmd == "/cwd":
        _console.print(f"[cyan]{os.getcwd()}[/cyan]")
    elif cmd == "/help":
        _console.print(Markdown(HELP_TEXT))
    else:
        _console.print(f"[yellow]Unknown command:[/yellow] {cmd}  (type /help)")


def _looks_like_markdown(text: str) -> bool:
    return any(m in text for m in ("```", "**", "##", "- ", "1. "))
