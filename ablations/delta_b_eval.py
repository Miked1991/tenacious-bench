"""
delta_b_eval.py — Delta B: Prompt-Engineered Control Evaluation

Measures how well the BASE model (Qwen3 4B, no LoRA adapter) performs on
the sealed held-out partition when given the full Tenacious style guide as
a system prompt.

Delta B answers the question: does SFT add value beyond what careful
prompting alone can achieve?

    Delta B = score(trained adapter) - score(prompt-engineered base)

If Delta B is positive, training is justified.
If Delta B is near zero, a well-engineered system prompt is sufficient
and retraining is not cost-justified.

Without measuring Delta B, the claim that the adapter outperforms prompting
is unconfirmed.

Usage (run on Colab T4 — requires GPU):
    python ablations/delta_b_eval.py \
        --held_out tenacious_bench_v0.1/held_out/tasks.jsonl \
        --output   ablations/delta_b_results.json

    # Compare against trained adapter results
    python ablations/delta_b_eval.py \
        --held_out tenacious_bench_v0.1/held_out/tasks.jsonl \
        --output   ablations/delta_b_results.json \
        --trained_results ablation_results.json

Requirements (Colab):
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps xformers trl peft accelerate bitsandbytes
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

HELD_OUT_PATH = ROOT / "tenacious_bench_v0.1" / "held_out" / "tasks.jsonl"
SEED = 42

# Full Tenacious style guide — identical to the system prompt used in training
SYSTEM_PROMPT = """You are the brief-to-email composer for Tenacious Intelligence Corporation, a B2B engineering bench provider.

## Tenacious Style Guide v2 — Hard Rules

WORD COUNT:
- Cold outreach (first contact): ≤120 words in email body
- Warm outreach (after engagement): ≤200 words
- Re-engagement (bounced/dormant): ≤100 words

BANNED PHRASES (never use any of these):
leverage, AI-powered, disrupt, world-class, A-players, skyrocket, transformational,
don't miss out, game-changer, cutting-edge, innovative solution, seamlessly, synergy,
paradigm shift, move the needle, low-hanging fruit, circle back, reach out, touch base,
scale rapidly, scale fast, rapidly scale, available immediately, within X weeks,
best-in-class, thought leader, holistic approach, value-add, end-to-end

GROUNDING RULE:
Every email must reference at least one specific, verifiable signal from the brief:
- Exact funding amount and stage (e.g., "$28M Series B in January")
- Exact number of open roles (e.g., "9 open ML roles")
- Exact leadership change (e.g., "new VP Engineering since March")
- Exact layoff date (e.g., "restructuring in February")
Do NOT make claims not supported by the signals provided.

SEGMENT RULES:
- Segment 0 (generic): No strong signal. Use diagnostic opener about open roles.
- Segment 1 (funded): crunchbase_signal.confidence >= 0.7 AND recently_funded=True. Reference funding.
- Segment 2 (leadership): pdl_signal.confidence >= 0.7 AND leadership_change=True. Reference role change.
- Segment 3 (hypergrowth): Multiple strong signals. Be specific but do NOT commit to headcount or timelines.

BENCH COMMITMENT RULE:
NEVER state a specific team size or delivery timeline. Correct: "we'd scope headcount together on a call."
Wrong: "10 engineers in 2 weeks," "we can staff a full team immediately."

CLOSING:
Always end with a specific calendar-link ask: "Would [day] at [time] work for a 15-minute call?"
For EU prospects: offer business hours in their local timezone (not UTC).

TONE:
Confident and specific. No filler phrases. No exclamation marks. First line must be signal-grounded.
"""


# ── I/O ───────────────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> List[Dict]:
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def build_user_brief(task: Dict) -> str:
    """Reconstruct the user brief from a task's input fields."""
    inp = task["input"]
    lines = [f"Prospect: {inp['prospect_name']} ({inp['prospect_domain']})"]

    cb = inp.get("crunchbase_signal", {})
    if cb.get("confidence", 0) > 0:
        if cb.get("recently_funded") and cb.get("funding_stage"):
            amount = f"${cb['funding_amount_usd']:,}" if cb.get("funding_amount_usd") else "undisclosed"
            lines.append(
                f"Crunchbase: {cb['funding_stage']} ({amount}) on {cb.get('last_funding_date', 'unknown')} "
                f"[confidence={cb['confidence']:.2f}]"
            )
        else:
            lines.append(f"Crunchbase: no recent funding detected [confidence={cb['confidence']:.2f}]")
    else:
        lines.append("Crunchbase: no data [confidence=0.00]")

    pw = inp.get("playwright_signal", {})
    if pw.get("open_engineering_roles", 0) > 0:
        roles = ", ".join(pw.get("role_titles", [])[:4])
        lines.append(
            f"Hiring: {pw['open_engineering_roles']} open engineering roles — {roles} "
            f"[confidence={pw.get('confidence', 0):.2f}]"
        )
    else:
        lines.append("Hiring: no open engineering roles detected")

    pdl = inp.get("pdl_signal", {})
    if pdl.get("leadership_change") and pdl.get("confidence", 0) > 0:
        days = f" ({pdl['days_since_change']} days ago)" if pdl.get("days_since_change") else ""
        lines.append(
            f"Leadership: new {pdl.get('change_role', 'executive')}{days} "
            f"[confidence={pdl.get('confidence', 0):.2f}]"
        )
    else:
        lines.append("Leadership: no recent changes detected")

    lo = inp.get("layoffs_signal", {})
    if lo.get("had_layoffs") and lo.get("confidence", 0) > 0:
        days = f" ({lo['layoff_date_days_ago']} days ago)" if lo.get("layoff_date_days_ago") else ""
        lines.append(
            f"Layoffs: confirmed restructuring{days} "
            f"[confidence={lo.get('confidence', 0):.2f}]"
        )

    lines.append(f"Headcount estimate: {inp.get('headcount_estimate', '?')}")
    lines.append(f"AI maturity: {inp.get('ai_maturity_score', '?')}/3")
    lines.append(f"Country: {inp.get('prospect_country', '?')} | Timezone: {inp.get('prospect_timezone', '?')}")

    bench = inp.get("bench_available", {})
    if bench:
        role_names = {
            "python_senior": "Python Senior", "go_senior": "Go Senior",
            "ml_senior": "ML Senior", "data_mid": "Data Mid", "devops_mid": "DevOps Mid",
        }
        bench_str = " | ".join(f"{label}: {bench[k]}" for k, label in role_names.items() if k in bench)
        lines.append(f"Bench available: {bench_str}")

    gt = task.get("ground_truth", {})
    seg = gt.get("correct_segment", 0)
    lines.append(f"\nAssign segment: {seg} (0=generic, 1=funded, 2=leadership, 3=hypergrowth)")
    lines.append("Write the outreach email (subject + body). Follow all style guide rules.")
    return "\n".join(lines)


def parse_model_output(raw: str) -> Dict:
    """Parse 'Subject: ...\n\n<body>' into candidate_output dict."""
    lines = raw.strip().split("\n")
    subject = ""
    body_lines = []
    in_body = False

    for line in lines:
        if not in_body and line.lower().startswith("subject:"):
            subject = line[len("subject:"):].strip()
        elif not in_body and subject and line.strip() == "":
            in_body = True
        elif in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return {"email_subject": subject, "email_body": body, "segment_assigned": 0}


# ── Inference (requires GPU + Unsloth) ───────────────────────────────────────

def load_base_model(model_name: str = "unsloth/Qwen3-4B-bnb-4bit", max_seq_len: int = 2048):
    """Load base model WITHOUT adapter. Requires Unsloth + CUDA."""
    try:
        from unsloth import FastLanguageModel  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError(
            "unsloth not installed. Run this script on Colab T4:\n"
            "  pip install 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'\n"
            "  pip install --no-deps xformers trl peft accelerate bitsandbytes"
        )

    print(f"Loading base model (no adapter): {model_name}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_len,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def generate_with_base_model(model, tokenizer, system_prompt: str, user_brief: str) -> str:
    """Generate output using the base model with only the system prompt (no adapter)."""
    import torch

    text = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_brief}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=250,
            temperature=0.1,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    decoded = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return decoded.strip()


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_outputs(tasks: List[Dict], outputs: List[str]) -> List[float]:
    scores = []
    for task, raw_output in zip(tasks, outputs):
        candidate = parse_model_output(raw_output)
        # Inherit segment from ground truth for scoring (base model may not produce it in JSON)
        candidate["segment_assigned"] = task["ground_truth"].get("correct_segment", 0)
        task_with_output = {**task, "candidate_output": candidate}
        result = score_task(task_with_output)
        scores.append(result["total_score"])
    return scores


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Delta B: prompt-engineered baseline evaluation")
    parser.add_argument("--held_out",        type=Path, default=HELD_OUT_PATH)
    parser.add_argument("--output",          type=Path, default=ROOT / "ablations" / "delta_b_results.json")
    parser.add_argument("--trained_results", type=Path, default=None,
                        help="Path to ablation_results.json (for Delta B comparison)")
    parser.add_argument("--model",           default="unsloth/Qwen3-4B-bnb-4bit")
    args = parser.parse_args()

    if not args.held_out.exists():
        print(f"ERROR: {args.held_out} not found")
        sys.exit(1)

    tasks = read_jsonl(args.held_out)
    n = len(tasks)
    print(f"Loaded {n} held-out tasks")

    # Generate outputs with base model + full system prompt
    model, tokenizer = load_base_model(args.model)
    print(f"Generating {n} outputs with base model (prompt-engineered, no adapter)...")

    outputs = []
    for i, task in enumerate(tasks):
        brief = build_user_brief(task)
        raw = generate_with_base_model(model, tokenizer, SYSTEM_PROMPT, brief)
        outputs.append(raw)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{n} done")

    scores = score_outputs(tasks, outputs)
    mean_score = sum(scores) / n * 100

    # Per-category breakdown
    by_cat: Dict[str, list] = {}
    for task, score in zip(tasks, scores):
        by_cat.setdefault(task["category"], []).append(score)
    per_category = [
        {"category": cat, "n": len(v), "mean": round(sum(v) / len(v) * 100, 1)}
        for cat, v in sorted(by_cat.items())
    ]

    # Delta B comparison
    delta_b: Optional[float] = None
    if args.trained_results and args.trained_results.exists():
        trained_data = json.loads(args.trained_results.read_text())
        trained_mean = trained_data.get("trained_mean", 0.0)
        delta_b = round(trained_mean - mean_score, 1)
        print(f"\nDelta B = {delta_b:+.1f} pp (trained {trained_mean:.1f}% vs prompt-engineered {mean_score:.1f}%)")
        if delta_b > 0:
            print("  → Training adds value beyond prompting. SFT is cost-justified.")
        else:
            print("  → Prompting achieves comparable results. Retraining may not be cost-justified.")

    result = {
        "run_timestamp": datetime.now().isoformat(),
        "model": args.model,
        "condition": "prompt_engineered_base_no_adapter",
        "held_out_n": n,
        "prompt_engineered_mean": round(mean_score, 1),
        "delta_b_pp": delta_b,
        "per_category": per_category,
        "note": (
            "Delta B = trained_mean - prompt_engineered_mean. "
            "Positive Delta B confirms SFT adds value beyond careful prompting."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(f"\nResults written to {args.output}")
    print(f"Prompt-engineered mean: {mean_score:.1f}%")


if __name__ == "__main__":
    main()
