# shadow-cli — Plan v2

> Builds on [plan_v1.md](plan_v1.md). Documents the switch from AWS Bedrock to the internal LLM gateway.

## What changed from v1

| Area | v1 (Bedrock) | v2 (Internal gateway) |
|---|---|---|
| Backend | AWS Bedrock `converse_stream` | Internal HTTP gateway (wraps Azure OpenAI) |
| Auth | AWS credentials (IAM + access keys) | `cmdbid` header + `apitoken` header |
| Tool schema format | Bedrock `toolSpec` / `inputSchema` | OpenAI `type: function` / `parameters` |
| Message format | Bedrock content blocks `[{"text": ...}]` | OpenAI strings `"content": "..."` |
| Tool results | Bedrock `toolResult` in user content | OpenAI `role: "tool"` messages |
| Key dependency | `boto3` | `requests` |
| Streaming format | Bedrock event stream | Line-delimited JSON `{"responsebody": {...}}` |

## Architecture

```
shadow-cli/
├── plans/
│   ├── plan_v1.md            ← original Bedrock design
│   └── plan_v2.md            ← this file
├── shadow/
│   ├── __init__.py
│   ├── cli.py                ← REPL (prompt_toolkit + rich)
│   ├── gateway.py            ← HTTP client for internal gateway
│   ├── bedrock.py            ← placeholder (superseded)
│   ├── conversation.py       ← message history + system prompt
│   ├── tools.py              ← tool schemas (OpenAI format) + implementations
│   └── config.py             ← ~/.shadow/config.json + env var overrides
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Gateway request structure

```json
{
  "requestid":       "<uuid4>",
  "requestdatetime": "2025-01-01 00:00:00+0000",
  "cmdbid":          "<your cmdb id>",
  "costcenter":      "<cost center>",
  "businessunit":    "<business unit>",
  "accgroup":        "<access group>",
  "userid":          "<user email>",
  "provider":        "azure-openai",
  "apicontext":      "chatcompletions",
  "requestbody": {
    "model":       "gpt-4o",
    "messages":    [...],
    "temperature": 0,
    "stream":      true,
    "n":           1,
    "max_tokens":  4096,
    "tools":       [...],
    "tool_choice": "auto"
  }
}
```

Headers: `cmdbid` + `apitoken`. Streaming: line-delimited JSON `{"responsebody": <OpenAI chunk>}`.

## Config (`~/.shadow/config.json`) — local only, never committed

```json
{
  "gateway_url":    "https://...",
  "api_token":      "...",
  "cmdb_id":        "...",
  "cost_center":    "...",
  "business_unit":  "...",
  "acc_group":      "...",
  "user_id":        "user@example.com",
  "model":          "gpt-4o",
  "provider":       "azure-openai",
  "max_tokens":     4096,
  "temperature":    0
}
```

Env var overrides (take precedence over config file):
- `SHADOW_GATEWAY_URL`
- `SHADOW_API_TOKEN`
- `SHADOW_CMDB_ID`

## Tool-use loop

1. POST to gateway (streaming)
2. Accumulate `delta.tool_calls` chunks by index
3. `finish_reason == "tool_calls"` → execute tools with confirmation for destructive ops
4. Append assistant message (with `tool_calls`) + `role: "tool"` result messages
5. Loop until `finish_reason == "stop"`

## Decisions

- **OpenAI message format**: The gateway wraps Azure OpenAI, so schemas and history follow the OpenAI spec directly.
- **Line-delimited JSON**: Each SSE chunk is wrapped in `{"responsebody": ...}` — parsed line by line.
- **SSL verify=False**: Internal gateway uses an internal TLS cert; urllib3 warnings suppressed.
- **No secrets in repo**: All auth lives in `~/.shadow/config.json` or env vars only.
