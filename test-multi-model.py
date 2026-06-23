import requests
import json
import time
import os
import sys
from datetime import datetime

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

ALL_MODELS = [
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B", "ctx": 131072, "size": "70B"},
    {"id": "google/gemma-4-31b-it:free", "name": "Gemma 4 31B", "ctx": 262144, "size": "31B"},
    {"id": "qwen/qwen3-coder:free", "name": "Qwen3 Coder 480B", "ctx": 1048576, "size": "480B"},
    {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super 120B", "ctx": 1000000, "size": "120B"},
    {"id": "openai/gpt-oss-120b:free", "name": "GPT-OSS 120B", "ctx": 131072, "size": "120B"},
    {"id": "nousresearch/hermes-3-llama-3.1-405b:free", "name": "Hermes 3 405B", "ctx": 131072, "size": "405B"},
    {"id": "qwen/qwen3-next-80b-a3b-instruct:free", "name": "Qwen3 Next 80B", "ctx": 262144, "size": "80B"},
    {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B", "ctx": 131072, "size": "3B"},
]

NO_SKILL = "You are a helpful coding assistant. Write clean code."

WITH_SKILL = """You are a coding assistant that follows the Pause & Think workflow.

RULES:
1. CLARIFY: Before coding, ask 1-2 questions if anything is ambiguous. Skip if obvious.
2. PLAN: Present a brief plan before writing code.
3. EXECUTE: Write code. If uncertain, ask — don't guess.
4. VERIFY: Before reporting done, check for errors and present summary.

NEVER jump to code without understanding. NEVER assume tech choices without asking."""

TASKS = [
    {"id": 1, "name": "Health endpoint", "prompt": "Add GET /api/health returning status, uptime, memory. Express server.", "size": "trivial", "files": 2, "loc": 18},
    {"id": 2, "name": "JWT auth", "prompt": "Add JWT auth. Protect /api/posts. POST /api/auth/login returns token. jsonwebtoken+bcryptjs.", "size": "small", "files": 3, "loc": 42},
    {"id": 3, "name": "Registration", "prompt": "Add user registration. Email validation, password hashing. POST /api/auth/register. Error messages.", "size": "medium", "files": 4, "loc": 85},
    {"id": 4, "name": "Rate limiting", "prompt": "Rate limit 100req/15min/IP. Input validation on POST. 429/400 responses with messages.", "size": "medium", "files": 4, "loc": 68},
    {"id": 5, "name": "Full CRUD", "prompt": "CRUD products with pagination, search, category filter. GET/POST/PUT/DELETE. Status codes.", "size": "large", "files": 5, "loc": 145},
]

BASE_CODE = """const express = require('express');
const app = express();
app.use(express.json());
app.get('/api/users', (req, res) => res.json({}));
app.get('/api/posts', (req, res) => res.json({}));
app.listen(3000);"""


def call_api(system, user, model_id):
    for attempt in range(3):
        try:
            resp = requests.post(API_URL, headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }, json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 2000,
                "temperature": 0.3,
            }, timeout=60)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                }
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                print(f"    Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                print(f"    HTTP {resp.status_code}: {resp.text[:100]}")
                time.sleep(5)
        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(5)
    return None


def analyze(text):
    t = text.lower()
    return {
        "questions": sum(1 for q in ["?", "do you", "should i", "which", "what db", "what database"] if q in t),
        "has_plan": any(p in t for p in ["plan:", "steps:", "1.", "2.", "3.", "here's my approach"]),
        "has_code": "```" in text,
        "assumptions": sum(1 for a in ["i'll use", "i will use", "using ", "i chose"] if a in t),
        "has_verify": any(v in t for v in ["test", "verify", "check", "error handling", "edge case"]),
        "asks_confirm": any(a in t for a in ["proceed?", "go ahead?", "shall i", "looks good?"]),
        "response_length": len(text),
    }


def run_single(model, mode):
    sys_prompt = NO_SKILL if mode == "without_skill" else WITH_SKILL
    results = []

    for task in TASKS:
        user_msg = f"{task['prompt']}\n\nExisting code:\n```\n{BASE_CODE}\n```"
        print(f"    [{mode[:3]}] {task['name']}...", end=" ", flush=True)

        result = call_api(sys_prompt, user_msg, model["id"])
        if result:
            a = analyze(result["content"])
            results.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "task_size": task["size"],
                "mode": mode,
                "tokens": result["usage"],
                "analysis": a,
            })
            print(f"✓ (tok:{result['usage'].get('total_tokens','?')}, Q:{a['questions']}, Plan:{a['has_plan']}, V:{a['has_verify']})")
        else:
            print("✗ FAILED")

        time.sleep(2)

    return results


def run_all():
    if not API_KEY:
        print("ERROR: Set OPENROUTER_API_KEY env var")
        sys.exit(1)

    print(f"Pause & Think — Multi-Model Test")
    print(f"Models: {len(ALL_MODELS)}")
    print(f"Tasks: {len(TASKS)}")
    print(f"Total API calls: {len(ALL_MODELS) * len(TASKS) * 2}")
    print(f"Started: {datetime.now().isoformat()}")
    print()

    all_results = []

    for model in ALL_MODELS:
        print(f"Model: {model['name']} ({model['id']})")

        # Without skill
        r1 = run_single(model, "without_skill")
        all_results.extend(r1)
        time.sleep(3)

        # With skill
        r2 = run_single(model, "with_skill")
        all_results.extend(r2)
        time.sleep(3)

        # Save intermediate
        save_data(all_results, model)
        print()

    print(f"Done: {len(all_results)} trials")
    return all_results


def save_data(results, last_model):
    output = {
        "metadata": {
            "models_tested": list(set(r.get("model", last_model["id"]) for r in results)),
            "tasks": len(TASKS),
            "total_trials": len(results),
            "timestamp": datetime.now().isoformat(),
        },
        "results": results,
    }
    with open("raw-data.json", "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    run_all()
