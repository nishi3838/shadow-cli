"""In-session conversation history and system prompt builder."""

import os
import platform


class Conversation:
    def __init__(self, cwd: str) -> None:
        self.messages: list[dict] = []
        self._cwd = cwd

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def replace_last_messages(self, updated: list[dict]) -> None:
        """Replace self.messages with the tool-loop-expanded version returned by GatewayClient."""
        self.messages = updated

    def system_prompt(self) -> str:
        os_name = platform.system()
        shell_hint = (
            "PowerShell or cmd.exe" if os_name == "Windows" else f"{os_name} shell"
        )
        return (
            "You are shadow, a terminal-based AI coding assistant.\n\n"
            f"Current working directory: {self._cwd}\n"
            f"Operating system: {os_name} ({shell_hint})\n\n"
            "You have access to tools that let you read files, list and search the "
            "codebase, write and edit files, and run shell commands. "
            "When writing shell commands, use syntax appropriate for the OS above. "
            "Always confirm with the user before making destructive changes.\n\n"
            "Be concise and direct. Prefer targeted edits over full rewrites unless "
            "a full rewrite is clearly better."
        )
