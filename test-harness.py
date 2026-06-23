import requests
import json
import time
import re
import os

API_KEY = "os.environ.get("OPENROUTER_API_KEY", "")"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# System prompts
NO_SKILL_PROMPT = "You are a helpful coding assistant. Write clean code."

WITH_SKILL_PROMPT = """You are a coding assistant that follows the Pause & Think workflow.

RULES:
1. CLARIFY: Before coding, ask 1-2 questions if anything is ambiguous. Skip if obvious.
2. PLAN: Present a brief plan before writing code. Wait for user confirmation.
3. EXECUTE: Write code. If uncertain, ask — don't guess.
4. VERIFY: Before reporting done, run tests if possible, check for errors, present summary.

NEVER:
- Jump to code without understanding
- Assume tech choices without asking
- Start coding before presenting a plan
- Report done without verification

When you receive a coding task:
- First: clarify if needed (max 2 questions)
- Then: present a brief plan
- Then: write code
- Finally: verify and summarize"""

# 5 coding tasks
TASKS = [
    {
        "id": 1,
        "name": "Health endpoint",
        "prompt": "Add a GET /api/health endpoint to this Express server that returns status, uptime in seconds, and memory usage in MB. The server uses Express and is in server.js.",
        "base_code": """const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;
app.use(express.json());
app.get('/api/users', (req, res) => res.json({ users: [] }));
app.get('/api/posts', (req, res) => res.json({ posts: [] }));
app.listen(PORT, () => console.log(`Server on ${PORT}`));""",
    },
    {
        "id": 2,
        "name": "JWT auth",
        "prompt": "Add JWT authentication middleware. Protect the /api/posts route. Create a POST /api/auth/login endpoint that accepts email+password and returns a JWT token. Use jsonwebtoken and bcryptjs packages.",
        "base_code": """const express = require('express');
const app = express();
app.use(express.json());
app.get('/api/users', (req, res) => res.json({ users: [] }));
app.get('/api/posts', (req, res) => res.json({ posts: [] }));
app.listen(3000);""",
    },
    {
        "id": 3,
        "name": "User registration",
        "prompt": "Add user registration with email validation and password hashing. POST /api/auth/register should validate email format, hash password with bcrypt, and store user. Add proper error messages for validation failures.",
        "base_code": """const express = require('express');
const app = express();
app.use(express.json());
app.get('/api/users', (req, res) => res.json({ users: [] }));
app.listen(3000);""",
    },
    {
        "id": 4,
        "name": "Rate limiting",
        "prompt": "Add rate limiting to all API routes: max 100 requests per 15 minutes per IP. Also add input validation on POST endpoints: require 'name' field (string, 1-100 chars) and 'email' field (valid email format). Return 429 for rate limit, 400 for validation errors.",
        "base_code": """const express = require('express');
const app = express();
app.use(express.json());
app.post('/api/items', (req, res) => res.json({ item: req.body }));
app.post('/api/orders', (req, res) => res.json({ order: req.body }));
app.listen(3000);""",
    },
    {
        "id": 5,
        "name": "CRUD + pagination",
        "prompt": "Add full CRUD for products (GET all with pagination, GET by id, POST create, PUT update, DELETE). Support query params: page, limit (default 10), search (by name), category filter. Return proper HTTP status codes and error messages.",
        "base_code": """const express = require('express');
const app = express();
app.use(express.json());
app.get('/api/products', (req, res) => res.json({ products: [] }));
app.listen(3000);""",
    },
]


def call_api(system_prompt, user_message):
    """Call OpenRouter API and return response + token usage."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 2000,
        "temperature": 0.3,
    }

    start = time.time()
    resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
    elapsed = time.time() - start

    if resp.status_code != 200:
        return None, elapsed

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    return {
        "content": content,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }, elapsed


def analyze_response(response_text):
    """Analyze an AI response for quality metrics."""
    text_lower = response_text.lower()

    # Check for clarifying questions
    question_indicators = ["?", "do you", "should i", "which", "what", "how"]
    questions = sum(1 for q in question_indicators if q in text_lower)

    # Check for plan
    plan_indicators = ["plan:", "steps:", "1.", "2.", "3.", "first,", "i'll"]
    has_plan = any(p in text_lower for p in plan_indicators)

    # Check for code
    has_code = "```" in response_text or "const " in response_text or "def " in response_text

    # Check for assumptions (tech choices without asking)
    assumption_patterns = [
        "i'll use", "i will use", "using ", "with ",
        "i chose", "i'll go with", "i'll create",
    ]
    assumptions = sum(1 for a in assumption_patterns if a in text_lower)

    # Check for verification
    verify_indicators = ["test", "verify", "check", "edge case", "error handling"]
    has_verify = any(v in text_lower for v in verify_indicators)

    # Check for summary
    has_summary = any(s in text_lower for s in ["created:", "modified:", "here's what", "summary:"])

    # Check for waiting/asking user
    asks_user = any(a in text_lower for a in ["proceed?", "go ahead?", "shall i", "looks good?"])

    return {
        "has_clarifying_questions": questions > 1,
        "question_count": questions,
        "has_plan": has_plan,
        "has_code": has_code,
        "assumption_count": assumptions,
        "has_verification": has_verify,
        "has_summary": has_summary,
        "asks_user_confirmation": asks_user,
    }


def run_test(trial_id, task, system_prompt, mode):
    """Run a single test trial."""
    print(f"  Trial {trial_id} ({mode}): {task['name']}...")

    user_msg = f"{task['prompt']}\n\nExisting code:\n```\n{task['base_code']}\n```"

    result, elapsed = call_api(system_prompt, user_msg)

    if result is None:
        print(f"    ERROR: API call failed ({elapsed:.1f}s)")
        return None

    analysis = analyze_response(result["content"])

    print(f"    Done ({elapsed:.1f}s, {result['total_tokens']} tokens)")
    print(f"    Questions: {analysis['question_count']}, Plan: {analysis['has_plan']}, "
          f"Assumptions: {analysis['assumption_count']}, Verify: {analysis['has_verification']}")

    return {
        "trial_id": trial_id,
        "task_name": task["name"],
        "task_size": ["trivial", "small", "medium", "medium", "large"][trial_id - 1],
        "mode": mode,
        "model": MODEL,
        "tokens": {
            "prompt": result["prompt_tokens"],
            "completion": result["completion_tokens"],
            "total": result["total_tokens"],
        },
        "elapsed_seconds": round(elapsed, 1),
        "analysis": analysis,
        "response_preview": result["content"][:500],
    }


def main():
    print(f"Model: {MODEL}")
    print(f"Tasks: {len(TASKS)}")
    print(f"Runs per task: 2 (without skill + with skill)")
    print()

    all_results = []

    for task in TASKS:
        print(f"Task {task['id']}: {task['name']}")

        # Without skill
        r1 = run_test(task["id"], task, NO_SKILL_PROMPT, "without_skill")
        if r1:
            all_results.append(r1)

        time.sleep(1)  # Rate limit courtesy

        # With skill
        r2 = run_test(task["id"], task, WITH_SKILL_PROMPT, "with_skill")
        if r2:
            all_results.append(r2)

        time.sleep(1)
        print()

    # Save raw data
    output = {
        "metadata": {
            "model": MODEL,
            "api": "OpenRouter",
            "tasks": len(TASKS),
            "trials_per_task": 2,
            "total_trials": len(all_results),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "results": all_results,
    }

    with open("/home/paong/pause-and-think-test/raw-data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to raw-data.json ({len(all_results)} trials)")
    return output


if __name__ == "__main__":
    main()
