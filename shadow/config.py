import json
import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

CONFIG_DIR = Path.home() / ".shadow"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Env-var overrides for sensitive values (never stored in the repo)
_ENV_OVERRIDES = {
    "gateway_url": "SHADOW_GATEWAY_URL",
    "api_token":   "SHADOW_API_TOKEN",
    "cmdb_id":     "SHADOW_CMDB_ID",
}

DEFAULTS = {
    # Gateway connection — fill these in locally; never commit real values
    "gateway_url":    "",
    "api_token":      "",
    "cmdb_id":        "",
    # Request metadata your gateway requires
    "cost_center":    "",
    "business_unit":  "",
    "acc_group":      "",
    "user_id":        "",
    # Model settings
    "model":          "gpt-4o",
    "provider":       "azure-openai",
    "max_tokens":     4096,
    "temperature":    0,
}

_console = Console()


def load() -> dict:
    stored = {}
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open() as f:
            stored = json.load(f)
    cfg = {**DEFAULTS, **stored}
    # Env vars always win for sensitive fields
    for key, env in _ENV_OVERRIDES.items():
        val = os.environ.get(env)
        if val:
            cfg[key] = val
    return cfg


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    to_save = {k: v for k, v in cfg.items() if k in DEFAULTS}
    with CONFIG_FILE.open("w") as f:
        json.dump(to_save, f, indent=2)


def first_run_wizard() -> dict:
    _console.print("\n[bold cyan]shadow first-time setup[/bold cyan]")
    _console.print(
        "Values are stored in [dim]~/.shadow/config.json[/dim] "
        "(never committed to the repo).\n"
        "You can also set [dim]SHADOW_GATEWAY_URL[/dim], "
        "[dim]SHADOW_API_TOKEN[/dim], [dim]SHADOW_CMDB_ID[/dim] as env vars.\n"
    )

    cfg = load()

    cfg["gateway_url"]   = Prompt.ask("Gateway URL",     default=cfg["gateway_url"])
    cfg["api_token"]     = Prompt.ask("API token",       default=cfg["api_token"],      password=True)
    cfg["cmdb_id"]       = Prompt.ask("CMDB ID",         default=cfg["cmdb_id"])
    cfg["cost_center"]   = Prompt.ask("Cost center",     default=cfg["cost_center"])
    cfg["business_unit"] = Prompt.ask("Business unit",   default=cfg["business_unit"])
    cfg["acc_group"]     = Prompt.ask("Access group",    default=cfg["acc_group"])
    cfg["user_id"]       = Prompt.ask("User ID (email)", default=cfg["user_id"])
    cfg["model"]         = Prompt.ask("Model",           default=cfg["model"])

    save(cfg)
    _console.print(f"[green]Config saved to {CONFIG_FILE}[/green]\n")
    return cfg


def ensure() -> dict:
    cfg = load()
    if not CONFIG_FILE.exists():
        cfg = first_run_wizard()
    elif not cfg.get("gateway_url") or not cfg.get("api_token"):
        _console.print(
            "[yellow]Warning:[/yellow] gateway_url or api_token is not set. "
            "Edit [dim]~/.shadow/config.json[/dim] or set "
            "[dim]SHADOW_GATEWAY_URL[/dim] / [dim]SHADOW_API_TOKEN[/dim]."
        )
    return cfg
