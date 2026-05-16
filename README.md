# shadow-cli

Terminal AI coding assistant powered by an internal LLM gateway. Works on Windows, macOS, and Linux.

```
shadow-cli/
├── shadow/      ← Python package
├── plans/       ← versioned design docs (plan_v1.md, plan_v2.md …)
└── README.md
```

---

## Prerequisites

- Python 3.10+
- Access to the internal LLM gateway (URL, API token, CMDB ID)

---

## Install

```bash
git clone https://github.com/nishi3838/shadow-cli.git
cd shadow-cli
pip install -e .
```

After install, `shadow` is available as a command from any directory.

---

## Setup — credentials and config

All sensitive values live in `~/.shadow/config.json` on your local machine. This file is **never committed to the repo**.

### Option A — first-run wizard (recommended)

Run `shadow` for the first time. If `~/.shadow/config.json` doesn't exist it will prompt you for each value:

```
Gateway URL      → https://your-internal-gateway/...
API token        → (hidden input)
CMDB ID          → APM0000000
Cost center      → 000000
Business unit    → YOURTEAM
Access group     → YourTeam-ACC_...
User ID (email)  → you@example.com
Model            → gpt-4o
```

### Option B — env vars

```bat
set SHADOW_GATEWAY_URL=https://your-internal-gateway/...
set SHADOW_API_TOKEN=your-token-here
set SHADOW_CMDB_ID=APM0000000
```

Env vars override the config file when both are present.

### Option C — edit the config file directly

Create or edit `~/.shadow/config.json`:

```json
{
  "gateway_url":    "https://your-internal-gateway/...",
  "api_token":      "your-token-here",
  "cmdb_id":        "APM0000000",
  "cost_center":    "000000",
  "business_unit":  "YOURTEAM",
  "acc_group":      "YourTeam-ACC_...",
  "user_id":        "you@example.com",
  "model":          "gpt-4o",
  "provider":       "azure-openai",
  "max_tokens":     4096,
  "temperature":    0
}
```

Delete the file to re-run the wizard.

---

## Usage

```bash
# cd to your project first — shadow uses this as context
cd C:\my-project
shadow
```

### In the REPL

```
you> read src/main.py and explain what it does
you> rename the function process_data to transform_data in utils.py
you> run: pip list
you> add error handling to the load_config function in config.py
```

### REPL Commands

| Command | Effect |
|---|---|
| `/help` | Show help |
| `/clear` | Clear conversation history (fresh context) |
| `/model` | Show active model |
| `/cwd` | Show working directory |
| `/exit` | Quit (also Ctrl-D) |

### Multi-line input

Press **Escape then Enter** to insert a newline. Press **Enter** alone to submit.

---

## Tools shadow can use

| Tool | What it does | Asks before running? |
|---|---|---|
| `read_file` | Read a file | No |
| `list_files` | List files in a directory | No |
| `grep` | Search for text in files | No |
| `write_file` | Write or create a file | **Yes** |
| `edit_file` | Replace a string in a file | **Yes** |
| `run_command` | Run a shell command | **Yes** |

---

## Versioned plans

The `plans/` directory contains design documents for each iteration:

- [plan_v1.md](plans/plan_v1.md) — original design (AWS Bedrock backend)
- [plan_v2.md](plans/plan_v2.md) — current design (internal LLM gateway)

When you evolve the design, add `plan_v3.md` etc.
