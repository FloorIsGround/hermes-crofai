# Hermes CrofAI

A [Hermes Agent](https://hermes-agent.nousresearch.com) provider plugin for [CrofAI](https://crof.ai) — powerful open-source LLMs at crazy cheap pricing.

Adds CrofAI as a first-class provider in Hermes, with auto-detected model listings, credential management, and full integration with `hermes doctor`, `hermes model`, and `hermes setup`.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/FloorIsGround/hermes-crofai/main/install.sh | bash
```

## Manual Install

Drop these two files into your Hermes plugins directory:

```bash
mkdir -p ~/.hermes/plugins/model-providers/crofai
curl -fsSL https://raw.githubusercontent.com/FloorIsGround/hermes-crofai/main/plugin.yaml \
  -o ~/.hermes/plugins/model-providers/crofai/plugin.yaml
curl -fsSL https://raw.githubusercontent.com/FloorIsGround/hermes-crofai/main/__init__.py \
  -o ~/.hermes/plugins/model-providers/crofai/__init__.py
```

## Setup

1. **Get an API key** — sign up at [crof.ai/signin](https://crof.ai/signin)
2. **Add your key** to `~/.hermes/.env`:
   ```
   CROFAI_API_KEY="your-key-here"
   ```
3. **Restart Hermes** and select CrofAI:
   ```bash
   hermes --provider crofai
   ```
   Or set it as your default:
   ```bash
   hermes config set model.provider crofai
   hermes config set model.default deepseek-v4-flash
   ```

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

## Files

```
hermes-crofai/
├── __init__.py     # Provider profile definition
├── plugin.yaml     # Plugin manifest
├── install.sh      # One-liner install script
└── README.md       # This file
```

## License

MIT
