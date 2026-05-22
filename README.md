# Hermes CrofAI

A [Hermes Agent](https://hermes-agent.nousresearch.com) provider plugin for [CrofAI](https://crof.ai) — powerful open-source LLMs at crazy cheap pricing.

Adds CrofAI as a first-class provider in Hermes, with auto-detected model listings, credential management, and full integration with `hermes doctor`, `hermes model`, and `hermes setup`.

## Quick Install (testing branch)

```bash
curl -fsSL https://raw.githubusercontent.com/FloorIsGround/hermes-crofai/testing/crofai-widget/install.sh | bash
hermes plugins enable crofai-widget
```

## Setup

1. **Get an API key** — sign up at [crof.ai/signin](https://crof.ai/signin)
2. **Add your key** to `~/.hermes/.env`:
   ```
   CROFAI_API_KEY="your-key-here"
   ```
3. **Set CrofAI as your provider:**
   ```bash
   hermes config set model.provider crofai
   hermes config set model.default deepseek-v4-flash
   ```
4. **Start the TUI with the usage widget:**
   ```bash
   hermes crof
   ```
   Or type `/crofai` in any Hermes session to see usage on demand.

## Verify

Run `hermes doctor` — you should see CrofAI listed under API Connectivity with a check mark.

## Models

The model list is fetched live from CrofAI's API on provider selection. Current models include:

| Model | Context | Quant |
|-------|---------|-------|
| DeepSeek V4 Pro | 1M | Q4_0 |
| DeepSeek V4 Pro (Precision) | 1M | Q8_0 |
| DeepSeek V4 Flash | 1M | Q4_0 |
| DeepSeek V3.2 | 164K | Q4_0 |
| Kimi K2.6 | 262K | Q3_K_L |
| Kimi K2.6 (Precision) | 262K | int4 |
| Kimi K2.5 | 262K | Q4_K_M |
| Kimi K2.5 (Lightning) | 131K | 530b-int4 |
| GLM 5.1 | 203K | Q6_K |
| GLM 5.1 (Precision) | 203K | Q8_0 |
| GLM 5 | 203K | Q4_0 |
| GLM 4.7 | 203K | Q8_0 |
| GLM 4.7 Flash | 203K | FP8 |
| Gemma 4 31B | 262K | Q4_0 |
| MiniMax M2.5 | 205K | AWQ |
| Qwen3.6 27B | 262K | Q4_0 |
| Qwen3.5 397B A17B | 262K | Q4_0 |
| Qwen3.5 9B | 262K | FP8 |
| MiMo V2.5 Pro | 1M | Q4_0 |
| MiMo V2.5 Pro (Precision) | 1M | Q8_0 |

Run `hermes model` after selecting CrofAI to see the full live list with pricing.

## What's supported

- Chat completions (streaming and non-streaming)
- Tool/function calling
- Structured outputs (JSON schema)
- Vision (on supported models)
- Reasoning effort control (`low`, `medium`, `high`, `none`)
- All standard parameters (`temperature`, `top_p`, `max_tokens`, `stop`, `seed`, `repetition_penalty`)

## TUI Widget Plugin

The companion `crofai-widget` plugin adds a persistent usage widget to the TUI status bar
showing live CrofAI credits and remaining requests. It also provides a `/crofai` slash command.

### How it works

The widget is baked into the TUI layout at startup via a `HermesCLI` subclass — no hook
timing issues. It refreshes automatically after each API call via a `post_api_request` hook.

| Feature | How to use |
|---------|-----------|
| `hermes crof` | Start the TUI with the persistent widget in the status bar |
| `/crofai` | Show credits + requests on demand in any session |

### Enable it

```bash
hermes plugins enable crofai-widget
```

Then run `hermes crof` to start the TUI with the widget.

### Debugging

If the widget doesn't appear, check the log:

```bash
grep "crofai-widget" ~/.hermes/logs/agent.log
```

## Files

```
hermes-crofai/
├── __init__.py             # Provider profile definition
├── plugin.yaml             # Model-provider plugin manifest
├── crofai-widget/
│   ├── __init__.py         # TUI widget plugin
│   └── plugin.yaml         # Widget plugin manifest
├── install.sh              # One-liner install script
├── README.md               # This file
└── LICENSE                 # MIT
```

## License

MIT
