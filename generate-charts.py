import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import os

BG = '#0d1117'
TEXT = '#e6edf3'
RED = '#ff6b6b'
GREEN = '#51cf66'
BLUE = '#58a6ff'
PURPLE = '#bc8cff'
ORANGE = '#f0883e'
GRAY = '#8b949e'
GRID = '#21262d'


def generate(data_file="raw-data.json", out_dir="charts"):
    os.makedirs(out_dir, exist_ok=True)

    with open(data_file) as f:
        data = json.load(f)

    results = data["results"]
    models = list(set(r.get("model", "?") for r in results))

    # ── Chart 1: Per-Model Aggregate ──
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.patch.set_facecolor(BG)
    fig.suptitle(f"Pause & Think — Multi-Model Results (n={len(results)} trials)", color=TEXT, fontsize=15, fontweight="bold", y=1.02)

    metrics = [
        ("Questions Asked", "questions", axes[0][0]),
        ("Has Plan", "has_plan", axes[0][1]),
        ("Assumptions", "assumptions", axes[0][2]),
        ("Has Verify", "has_verify", axes[1][0]),
        ("Asks Confirm", "asks_confirm", axes[1][1]),
        ("Response Length", "response_length", axes[1][2]),
    ]

    model_labels = [m.split("/")[-1].replace(":free", "")[:15] for m in sorted(models)]
    x = np.arange(len(model_labels))
    w = 0.35

    for title, key, ax in metrics:
        ax.set_facecolor(BG)
        without_vals = []
        with_vals = []
        for m in sorted(models):
            m_without = [r["analysis"][key] for r in results if r.get("model") == m and r["mode"] == "without_skill"]
            m_with = [r["analysis"][key] for r in results if r.get("model") == m and r["mode"] == "with_skill"]
            without_vals.append(sum(m_without) / len(m_without) if m_without else 0)
            with_vals.append(sum(m_with) / len(m_with) if m_with else 0)

        ax.bar(x - w/2, without_vals, w, color=RED, alpha=0.85, label="Without")
        ax.bar(x + w/2, with_vals, w, color=GREEN, alpha=0.85, label="With")
        ax.set_xticks(x)
        ax.set_xticklabels(model_labels, color=TEXT, fontsize=7, rotation=45, ha="right")
        ax.set_title(title, color=TEXT, fontsize=11, fontweight="bold")
        ax.legend(fontsize=7, facecolor="#161b22", edgecolor=GRID)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        for s in ["left", "bottom"]:
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=TEXT)
        ax.yaxis.grid(True, color=GRID, alpha=0.5)
        ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(f"{out_dir}/multi-model-results.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()

    # ── Chart 2: Task Size Impact ──
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    sizes = ["trivial", "small", "medium", "medium", "large"]
    task_names = ["Health", "JWT Auth", "Registration", "Rate Limit", "CRUD"]

    for mode, color, label in [("without_skill", RED, "Without Skill"), ("with_skill", GREEN, "With Skill")]:
        qs = []
        for i, size in enumerate(sizes):
            vals = [r["analysis"]["questions"] for r in results if r["task_size"] == size and r["mode"] == mode]
            qs.append(sum(vals) / len(vals) if vals else 0)
        x = np.arange(len(task_names))
        ax.plot(x, qs, marker="o", color=color, linewidth=2, markersize=8, label=label, alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(task_names, color=TEXT)
    ax.set_ylabel("Avg Questions", color=TEXT)
    ax.set_title("Questions by Task Size (across all models)", color=TEXT, fontsize=13, fontweight="bold", pad=15)
    ax.legend(fontsize=10, facecolor="#161b22", edgecolor=GRID)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TEXT)
    ax.yaxis.grid(True, color=GRID, alpha=0.5)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(f"{out_dir}/task-size-impact.png", dpi=150, facecolor=BG)
    plt.close()

    # ── Chart 3: Model Compliance Score ──
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    compliance = {}
    for m in sorted(models):
        m_results = [r for r in results if r.get("model") == m]
        w_score = np.mean([
            1 if r["analysis"]["has_plan"] else 0,
            1 if r["analysis"]["has_verify"] else 0,
            1 if r["analysis"]["asks_confirm"] else 0,
            max(0, 1 - r["analysis"]["assumptions"] / 5),
        ]) * 100 for r in m_results if r["mode"] == "without_skill"]

        s_results = [r for r in m_results if r["mode"] == "with_skill"]
        s_score = np.mean([
            1 if r["analysis"]["has_plan"] else 0,
            1 if r["analysis"]["has_verify"] else 0,
            1 if r["analysis"]["asks_confirm"] else 0,
            max(0, 1 - r["analysis"]["assumptions"] / 5),
        ]) * 100 for r in s_results]

        short = m.split("/")[-1].replace(":free", "")[:15]
        compliance[short] = {"without": w_score, "with": s_score}

    labels = list(compliance.keys())
    w_scores = [compliance[l]["without"] for l in labels]
    s_scores = [compliance[l]["with"] for l in labels]
    x = np.arange(len(labels))

    ax.barh(x + 0.2, w_scores, 0.35, color=RED, alpha=0.85, label="Without Skill")
    ax.barh(x - 0.2, s_scores, 0.35, color=GREEN, alpha=0.85, label="With Skill")

    for i, (w, s) in enumerate(zip(w_scores, s_scores)):
        ax.text(w + 1, i + 0.2, f"{w:.0f}%", va="center", color=RED, fontsize=9, fontweight="bold")
        ax.text(s + 1, i - 0.2, f"{s:.0f}%", va="center", color=GREEN, fontsize=9, fontweight="bold")

    ax.set_yticks(x)
    ax.set_yticklabels(labels, color=TEXT, fontsize=9)
    ax.set_xlabel("Compliance Score (%)", color=TEXT)
    ax.set_title("Workflow Compliance by Model", color=TEXT, fontsize=13, fontweight="bold", pad=15)
    ax.set_xlim(0, 110)
    ax.legend(fontsize=10, facecolor="#161b22", edgecolor=GRID)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TEXT)
    ax.xaxis.grid(True, color=GRID, alpha=0.5)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(f"{out_dir}/model-compliance.png", dpi=150, facecolor=BG)
    plt.close()

    print(f"3 charts saved to {out_dir}/")


if __name__ == "__main__":
    generate()
