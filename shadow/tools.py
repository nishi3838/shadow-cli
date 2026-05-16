"""Tool schemas (sent to the LLM) and their Python implementations."""

import fnmatch
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax

_console = Console()

# ---------------------------------------------------------------------------
# Schemas — OpenAI function-calling format, passed in requestbody.tools
# ---------------------------------------------------------------------------

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use relative paths from the project root or absolute paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory, optionally filtered by a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: current working directory)",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern filter, e.g. '*.py'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for a text pattern in files under a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search (default: current working directory)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a file with the given content. Will ask the user to confirm before writing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {
                        "type": "string",
                        "description": "Full content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in a file with a new string. "
                "old_str must be unique in the file. Will ask the user to confirm before editing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_str": {
                        "type": "string",
                        "description": "Exact string to find and replace",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Replacement string",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command. Will ask the user to confirm before executing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to run",
                    },
                },
                "required": ["command"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if not p.is_file():
        return f"Error: path is not a file: {path}"
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Error reading file: {exc}"


def list_files(path: str = ".", pattern: str = "*") -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: path not found: {path}"
    try:
        entries = sorted(p.rglob(pattern))
        lines = [str(e.relative_to(p)) for e in entries if e.is_file()]
        if not lines:
            return f"No files matching '{pattern}' found under {path}"
        return "\n".join(lines)
    except Exception as exc:
        return f"Error listing files: {exc}"


def grep(pattern: str, path: str = ".") -> str:
    p = Path(path)
    results: list[str] = []
    try:
        targets = [p] if p.is_file() else list(p.rglob("*"))
        for target in targets:
            if not target.is_file():
                continue
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pattern in line:
                    results.append(f"{target}:{i}: {line}")
    except Exception as exc:
        return f"Error during grep: {exc}"
    if not results:
        return f"No matches for '{pattern}' in {path}"
    return "\n".join(results[:200])


def write_file(path: str, content: str) -> str:
    _console.print(f"\n[bold yellow]write_file[/bold yellow] → [cyan]{path}[/cyan]")
    _console.print(Syntax(content[:2000], _guess_lexer(path), line_numbers=True))
    if len(content) > 2000:
        _console.print(f"[dim]... ({len(content)} chars total)[/dim]")

    if not Confirm.ask("Apply this write?", default=True):
        return "User cancelled write."

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written {len(content)} chars to {path}"


def edit_file(path: str, old_str: str, new_str: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"

    text = p.read_text(encoding="utf-8")
    count = text.count(old_str)
    if count == 0:
        return f"Error: old_str not found in {path}"
    if count > 1:
        return f"Error: old_str is not unique in {path} ({count} occurrences). Provide more context."

    _console.print(f"\n[bold yellow]edit_file[/bold yellow] → [cyan]{path}[/cyan]")
    _console.print("[red]- " + old_str.replace("\n", "\n- ") + "[/red]")
    _console.print("[green]+ " + new_str.replace("\n", "\n+ ") + "[/green]")

    if not Confirm.ask("Apply this edit?", default=True):
        return "User cancelled edit."

    p.write_text(text.replace(old_str, new_str, 1), encoding="utf-8")
    return f"Edit applied to {path}"


def run_command(command: str) -> str:
    _console.print(f"\n[bold yellow]run_command[/bold yellow] → [cyan]{command}[/cyan]")

    if not Confirm.ask("Run this command?", default=True):
        return "User cancelled command."

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        output += f"\n[exit code {result.returncode}]"
    return output or "(no output)"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

DISPATCH = {
    "read_file":   lambda i: read_file(**i),
    "list_files":  lambda i: list_files(**i),
    "grep":        lambda i: grep(**i),
    "write_file":  lambda i: write_file(**i),
    "edit_file":   lambda i: edit_file(**i),
    "run_command": lambda i: run_command(**i),
}


def execute(name: str, inputs: dict) -> str:
    fn = DISPATCH.get(name)
    if fn is None:
        return f"Error: unknown tool '{name}'"
    try:
        return fn(inputs)
    except Exception as exc:
        return f"Error executing {name}: {exc}"


def _guess_lexer(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".json": "json", ".md": "markdown", ".sh": "bash",
        ".yml": "yaml", ".yaml": "yaml", ".toml": "toml",
    }.get(ext, "text")
