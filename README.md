# Pause & Think — API Test Framework

Test harness for validating the Pause & Think skill using OpenRouter API with free models.

## Status

**Blocked:** Free tier rate limit exceeded (50 req/day). Account has no credits.

**To run:** Add $10 credits at https://openrouter.ai/settings/credits to unlock 1000 free model requests/day.

## How It Works

1. Sends 5 coding tasks to OpenRouter API
2. Each task tested twice: without skill vs with skill system prompt
3. Measures: questions asked, plan present, assumptions, verification
4. Saves raw data to `raw-data.json`
5. Generates comparison charts

## Models

Primary: `meta-llama/llama-3.3-70b-instruct:free`
Fallback: `google/gemma-4-31b-it:free`, `qwen/qwen3-coder:free`

## Run

```bash
export OPENROUTER_API_KEY="your-key"
python3 test.py
```

## Output

- `raw-data.json` — raw trial data
- `charts/` — comparison charts (generated after test)

## Methodology

- **Model:** Llama 3.3 70B (free tier)
- **Trials:** 5 tasks × 2 modes = 10 API calls
- **Scoring:** Automated analysis of response text
- **Baseline:** Same tasks without Pause & Think system prompt
