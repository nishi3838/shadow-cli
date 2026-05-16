# shadow-cli — Plan v1

> Design document. Add `plan_v2.md`, `plan_v3.md` etc. for future iterations.
> **Note:** v1 used AWS Bedrock as the backend. Superseded by [plan_v2.md](plan_v2.md).

## Context

Build a terminal-based AI coding assistant (like Cursor / Claude Code) powered by AWS Bedrock.
Runs on Windows (company PC) via a simple `shadow` CLI command. No IDE panel — pure terminal REPL.

## Architecture

```
shadow-cli/
├── plans/
│   └── plan_v1.md
├── shadow/
│   ├── __init__.py
│   ├── cli.py                ← REPL loop (prompt_toolkit + rich)
│   ├── bedrock.py            ← Bedrock converse_stream + tool-use loop
│   ├── conversation.py       ← message history + system prompt
│   ├── tools.py              ← tool schemas + Python implementations
│   └── config.py             ← ~/.shadow/config.json, first-run wizard
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Key Libraries

| Library | Purpose |
|---|---|
| `boto3` | AWS Bedrock SDK |
| `rich` | Coloured output, markdown rendering |
| `prompt_toolkit` | Multiline input, history (Windows-compatible) |

## AI Integration

- API: `bedrock-runtime.converse_stream`
- Default model: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Tool schemas: Bedrock `toolSpec` / `inputSchema` format

## Decisions & Trade-offs

- **Python over Node**: boto3 is the most mature Bedrock SDK.
- **converse_stream**: Native tool-use support, cleaner streaming event model.
- **Confirmation gate on destructive tools**: Prevents accidental overwrites.
- **In-memory history only**: Keeps it simple. Persistent sessions can be added later.
