import requests
import json
import time
import os
import sys

API_KEY = os.environ.get("OPENROUTER_API_KEY", "os.environ.get("OPENROUTER_API_KEY", "")")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Models to test (fallback chain)
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-31b-it:free",
    "qwen/qwen3-coder:free",
]

NO_SKILL_SYSTEM = "You are a helpful coding assistant. Write clean code."

WITH_SKILL_SYSTEM = """You are a coding assistant that follows the Pause & Think workflow.

RULES:
1. CLARIFY: Before coding, ask 1-2 questions if anything is ambiguous. Skip if obvious.
2. PLAN: Present a brief plan before writing code.
3. EXECUTE: Write code. If uncertain, ask — don't guess.
4. VERIFY: Before reporting done, check for errors and present summary.

NEVER jump to code without understanding. NEVER assume tech choices without asking."""

TASKS = [
    {"id": 1, "name": "Health endpoint", "prompt": "Add a GET /api/health endpoint returning status, uptime, memory. Express server in server.js.", "size": "trivial"},
    {"id": 2, "name": "JWT auth", "prompt": "Add JWT auth middleware. Protect /api/posts. POST /api/auth/login returns JWT. Use jsonwebtoken+bcryptjs.", "size": "small"},
    {"id": 3, "name": "Registration", "prompt": "Add user registration with email validation and password hashing. POST /api/auth/register. Return proper error messages.", "size": "medium"},
    {"id": 4, "name": "Rate limiting", "prompt": "Add rate limiting (100 req/15min/IP) and input validation on POST endpoints. Return 429/400 with messages.", "size": "medium"},
    {"id": 5, "name": "Full CRUD", "prompt": "Add full CRUD for products with pagination, search, category filter. GET/POST/PUT/DELETE. Proper status codes.", "size": "large"},
]


def call_api(system, user, model):
    for m in [model] + MODELS:
        try:
            resp = requests.post(API_URL, headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }, json={
                "model": m,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": 2000,
                "temperature": 0.3,
            }, timeout=60)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "model_used": m,
                }, resp.status_code
            elif resp.status_code == 429:
                time.sleep(5)
                continue
        except Exception as e:
            continue
    return None, 429


def analyze(text):
    t = text.lower()
    return {
        "questions": sum(1 for q in ["?", "do you", "should i", "which"] if q in t),
        "has_plan": any(p in t for p in ["plan:", "steps:", "1.", "2.", "3."]),
        "has_code": "```" in text or "const " in text,
        "assumptions": sum(1 for a in ["i'll use", "i will use", "using "] if a in t),
        "has_verify": any(v in t for v in ["test", "verify", "check", "error"]),
        "asks_confirm": any(a in t for a in ["proceed?", "go ahead?", "shall i"]),
    }


def run(model_override=None):
    model = model_override or MODELS[0]
    results = []

    for task in TASKS:
        for mode in ["without_skill", "with_skill"]:
            sys = NO_SKILL_SYSTEM if mode == "without_skill" else WITH_SKILL_SYSTEM
            user = f"{task['prompt']}\n\nExisting code:\nconst express = require('express');\nconst app = express();\napp.use(express.json());\napp.get('/api/users', (req, res) => res.json({}));\napp.listen(3000);"

            print(f"  [{mode}] {task['name']}...", end=" ", flush=True)
            result, status = call_api(sys, user, model)

            if result:
                a = analyze(result["content"])
                results.append({
                    "task_id": task["id"], "task_name": task["name"], "task_size": task["size"],
                    "mode": mode, "model": result["model_used"],
                    "tokens": result["usage"],
                    "analysis": a,
                })
                print(f"OK ({result['usage'].get('total_tokens', '?')} tok, Q:{a['questions']}, Plan:{a['has_plan']}, V:{a['has_verify']})")
            else:
                print(f"FAIL ({status})")

            time.sleep(2)

    return results


if __name__ == "__main__":
    print(f"Pause & Think — API Test Harness")
    print(f"Model: {MODELS[0]}")
    print()

    results = run()

    output = {
        "metadata": {"model": MODELS[0], "tasks": len(TASKS), "total_trials": len(results), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "results": results,
    }

    with open("raw-data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone: {len(results)} trials saved")
