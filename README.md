# Pause & Think — Multi-Model Test Framework

Validates the Pause & Think skill by testing across multiple free models on OpenRouter.

## Models Tested

| Model | Size | Context |
|-------|------|---------|
| Llama 3.3 70B Instruct | 70B | 131K |
| Gemma 4 31B | 31B | 262K |
| Qwen3 Coder 480B | 480B | 1M |
| Nemotron 3 Super 120B | 120B | 1M |
| GPT-OSS 120B | 120B | 131K |
| Hermes 3 405B | 405B | 131K |
| Qwen3 Next 80B | 80B | 262K |
| Llama 3.2 3B | 3B | 131K |

## Tasks Tested

| Task | Size | Files | LOC |
|------|------|-------|-----|
| Health endpoint | Trivial | 2 | 18 |
| JWT auth middleware | Small | 3 | 42 |
| User registration | Medium | 4 | 85 |
| Rate limiting | Medium | 4 | 68 |
| Full CRUD + pagination | Large | 5 | 145 |

## Scoring Criteria

For each API response, automated analysis checks:

- **Questions asked** — clarify questions in response
- **Has plan** — plan/steps section present
- **Has code** — code block present
- **Assumptions** — tech choices made without asking
- **Has verify** — verification/testing mentioned
- **Asks confirm** — user confirmation requested

## How to Run

```bash
# Set API key
export OPENROUTER_API_KEY="sk-or-v1-..."

# Run multi-model test (all 8 models × 5 tasks × 2 modes = 80 API calls)
python3 test-multi-model.py

# Generate charts from results
python3 generate-charts.py
```

**Note:** Free tier has 50 req/day limit. With $10 credits: 1000 req/day. Full test needs ~80 calls.

## Output

- `raw-data.json` — complete trial data
- `charts/multi-model-results.png` — per-model comparison (6 metrics)
- `charts/task-size-impact.png` — questions by task complexity
- `charts/model-compliance.png` — workflow compliance scores

## Methodology

- Same 5 tasks sent to each model
- Each task tested twice: without skill vs with skill system prompt
- System prompts are the only variable
- Temperature 0.3 for consistency
- Max 2000 tokens per response
- 2s delay between calls for rate limit courtesy

## Rate Limits

| Tier | Free Models/Day | Cost |
|------|:---:|------|
| Free (no credits) | 50 | $0 |
| With $10 credits | 1,000 | $10 one-time |

Add credits: https://openrouter.ai/settings/credits
