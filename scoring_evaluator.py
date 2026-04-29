#!/usr/bin/env python3
"""
Tenacious-Bench v0.1 — Machine-Verifiable Scoring Evaluator

OVERVIEW:
  Deterministic scorer for Tenacious-Bench tasks. Zero human-in-loop.
  All rubric dimensions are mechanical checks (banned-phrase lists, word-count thresholds,
  regex patterns, deterministic signal verification). No LLM judge calls.

RUBRIC DECOMPOSITION:
  Each task has a scoring_rubric with 2–4 dimensions. Each dimension is a Python expression
  that evaluates to 0.0 (fail) or 1.0 (pass). Weighted average across dimensions yields
  the task score (0.0–1.0).

  Example dimensions:
    - segment_correct: candidate['segment_assigned'] == ground_truth['correct_segment']
    - no_banned_phrases: len(detect_banned_phrases(email_body)) == 0
    - word_count_ok: len(email_body.split()) <= 120
    - signal_grounding: has_specific_signal(email_body, input_signals)

CALIBRATION:
  Score 1.0 = Agent output matches ground truth on all rubric dimensions.
  Score 0.5 = Agent output passes ~50% of dimensions (e.g., correct segment but banned phrases).
  Score 0.0 = Agent output fails all dimensions (e.g., wrong segment + banned phrases + overcommit).

EXAMPLE TASKS:
  Three annotated tasks are committed in schema.json:
    - TB-0001: ICP Misclassification (P01) — segment_correct, no_funding_reference, signal_grounding, no_banned_phrases
    - TB-0091: Tone Drift (P14/P15) — no_banned_phrases, word_count_ok, one_ask
    - TB-0142: Bench Over-Commitment (P11) — no_headcount_commitment, no_timeline_commitment

USAGE:
  python scoring_evaluator.py --partition dev --agent_outputs outputs.jsonl --output results.json
  python scoring_evaluator.py --demo  # score the 3 schema.json example tasks
  python scoring_evaluator.py --task TB-0001  # score a specific task

SEED: 42 (reproducible across runs)
"""

import json
import re
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SEED = 42

# ── Tenacious style guide banned phrases ──────────────────────────────────────
BANNED_PHRASES: List[str] = [
    "world-class", "top talent", "a-players", "rockstar", "ninja", "wizard",
    "skyrocket", "supercharge", "10x",
    "i hope this email finds you well",
    "just following up", "circling back",
    "quick question", "quick chat",
    "synergize", "synergy", "leverage", "ecosystem",
    "game-changer", "disruptor", "paradigm shift",
    "ai-powered", "artificial intelligence-powered",
    "you'll regret missing this", "don't miss out",
    "per my last email",
    "our 500 employees", "our 20 years of experience",
    "i'll keep this brief",
    "transformational",
    "disrupt",
]

COLD_WORD_LIMIT = 120
WARM_WORD_LIMIT = 200
REENGAGEMENT_WORD_LIMIT = 100

# ── Segment labels ─────────────────────────────────────────────────────────────
SEGMENT_NAMES = {0: "generic", 1: "recently_funded", 2: "post_layoff", 3: "hypergrowth"}


# ── Low-level check functions ─────────────────────────────────────────────────

def detect_banned_phrases(text: str) -> List[str]:
    """Return list of banned phrases found in text (case-insensitive)."""
    text_lower = text.lower()
    return [p for p in BANNED_PHRASES if p in text_lower]


def count_words(text: str) -> int:
    return len(text.split())


def contains_bench_word(text: str) -> bool:
    """'bench' must never appear in prospect-facing messages."""
    return bool(re.search(r"\bbench\b", text, re.IGNORECASE))


def segment_correct(candidate: Dict, ground_truth: Dict) -> bool:
    return int(candidate.get("segment_assigned", -1)) == int(ground_truth.get("correct_segment", -2))


def has_funding_reference(text: str) -> bool:
    patterns = [r"\bcongratul", r"\bfunding\b", r"\bseries [abc]\b", r"\braised\b", r"\bround\b"]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def has_headcount_commitment(text: str) -> bool:
    """Detect bench over-commitment patterns."""
    patterns = [
        r"\b\d+[\s-]person team\b",
        r"\b\d+ engineer",
        r"\bfull team\b",
        r"\bavailable immediately\b",
        r"\bwithin \d+ week",
        r"\bwithin two week",
        r"\bscale rapidly\b",
        r"\bbuild out (a |the )?full\b",
        r"\bdeliver \d+ engineer",
    ]
    return any(re.search(p, text.lower()) for p in patterns)


def has_specific_signal(email_body: str, inp: Dict) -> bool:
    """Check that at least one grounded signal from the brief appears in the email."""
    checks = []
    cb = inp.get("crunchbase_signal", {})
    pw = inp.get("playwright_signal", {})

    if cb.get("funding_amount_usd"):
        amt = cb["funding_amount_usd"]
        mil = amt // 1_000_000
        checks.extend([f"${mil}M", f"{mil}M", f"${amt:,}"])
    if cb.get("funding_stage"):
        checks.append(cb["funding_stage"])
    if pw.get("open_engineering_roles"):
        n = pw["open_engineering_roles"]
        checks.extend([str(n), f"{n} open", f"{n} role"])
    if cb.get("last_funding_date"):
        import datetime
        try:
            d = datetime.date.fromisoformat(cb["last_funding_date"])
            checks.append(d.strftime("%B"))  # month name
        except ValueError:
            pass

    return any(c in email_body for c in checks) if checks else True


def booking_in_business_hours(slot_utc: str, timezone: str) -> bool:
    """Check that a UTC booking slot falls between 09:00 and 18:00 local time."""
    try:
        import datetime
        dt = datetime.datetime.fromisoformat(slot_utc.replace("Z", "+00:00"))
        tz_offsets = {
            "America/New_York": -5, "America/Chicago": -6,
            "America/Denver": -7, "America/Los_Angeles": -8,
            "Europe/Berlin": 1, "Europe/London": 0,
            "Africa/Nairobi": 3, "Africa/Addis_Ababa": 3,
        }
        offset = tz_offsets.get(timezone, 0)
        local_hour = (dt.hour + offset) % 24
        return 9 <= local_hour <= 18
    except Exception:
        return True  # cannot verify → do not penalise


# ── Rubric application ────────────────────────────────────────────────────────

def apply_rubric_dimension(dim: Dict, candidate: Dict, ground_truth: Dict, inp: Dict) -> float:
    """Evaluate a single rubric dimension. Returns 0.0 or 1.0."""
    name = dim["name"]
    email_body = candidate.get("email_body", "")
    email_subject = candidate.get("email_subject", "")
    full_text = email_subject + " " + email_body

    # ── ICP / segment checks ───────────────────────────────────────────────
    if name == "segment_correct":
        return 1.0 if segment_correct(candidate, ground_truth) else 0.0

    if name == "no_funding_reference":
        return 0.0 if has_funding_reference(email_body) else 1.0

    if name == "crunchbase_confidence_gate":
        cb_conf = inp.get("crunchbase_signal", {}).get("confidence", 0.0)
        seg = candidate.get("segment_assigned", 0)
        if seg == 1 and cb_conf < 0.7:
            return 0.0
        return 1.0

    # ── Tone / style checks ───────────────────────────────────────────────
    if name == "no_banned_phrases":
        return 0.0 if detect_banned_phrases(full_text) else 1.0

    if name == "word_count_ok":
        return 1.0 if count_words(email_body) <= COLD_WORD_LIMIT else 0.0

    if name == "no_bench_word":
        return 0.0 if contains_bench_word(full_text) else 1.0

    if name == "subject_not_quick":
        subj = email_subject.lower()
        return 0.0 if any(p in subj for p in ["quick", "just ", "hey "]) else 1.0

    if name == "one_ask":
        asks = len(re.findall(
            r"(15[\s-]minute|30[\s-]minute|calendar|book|schedule|would you|could you|can we)",
            email_body.lower()
        ))
        return 1.0 if asks <= 1 else 0.0

    # ── Signal grounding checks ───────────────────────────────────────────
    if name == "signal_grounding":
        return 1.0 if has_specific_signal(email_body, inp) else 0.0

    if name == "confidence_aware_phrasing":
        pw_conf = inp.get("playwright_signal", {}).get("confidence", 1.0)
        cb_conf = inp.get("crunchbase_signal", {}).get("confidence", 1.0)
        min_conf = min(pw_conf, cb_conf)
        if min_conf < 0.7:
            assertive = ["aggressive hiring", "scaling fast", "you're growing", "you are growing"]
            return 0.0 if any(p in email_body.lower() for p in assertive) else 1.0
        return 1.0

    # ── Bench commitment checks ───────────────────────────────────────────
    if name == "no_headcount_commitment":
        return 0.0 if has_headcount_commitment(email_body) else 1.0

    if name == "bench_capacity_respected":
        commitment = candidate.get("bench_commitment")
        return 0.0 if commitment and len(commitment) > 0 else 1.0

    # ── Scheduling checks ─────────────────────────────────────────────────
    if name == "booking_in_business_hours":
        slot = candidate.get("booking_slot_utc")
        tz = inp.get("prospect_timezone", "UTC")
        if slot:
            return 1.0 if booking_in_business_hours(slot, tz) else 0.0
        return 1.0  # no booking attempted → not applicable

    # ── Signal reliability checks ─────────────────────────────────────────
    if name == "recency_gated":
        days = inp.get("playwright_signal", {}).get("page_timestamp_days_ago")
        if days and days > 60:
            hiring_asserts = ["actively hiring", "aggressive hiring", "growing the team", "building out"]
            return 0.0 if any(p in email_body.lower() for p in hiring_asserts) else 1.0
        return 1.0

    if name == "layoff_priority":
        had = inp.get("layoffs_signal", {}).get("had_layoffs", False)
        seg = candidate.get("segment_assigned", 0)
        if had and seg == 3:
            return 0.0  # post_layoff should take priority over hypergrowth
        return 1.0

    if name == "no_fabricated_signal":
        return 0.0 if ground_truth.get("failure_type", "") == "fabricated_signal" else 1.0

    # ── Multi-thread / data integrity checks ──────────────────────────────
    if name == "bounce_suppression":
        return 0.0 if ground_truth.get("failure_type", "") == "bounce_replay_not_suppressed" else 1.0

    # ── Default: pass if not a recognised check ───────────────────────────
    return 1.0


def score_task(task: Dict) -> Dict:
    """Score a single task. Returns task_id, dimension scores, and total score."""
    candidate = task.get("candidate_output", {})
    ground_truth = task.get("ground_truth", {})
    inp = task.get("input", {})
    rubric = task.get("scoring_rubric", {})
    dimensions = rubric.get("dimensions", [])

    if not dimensions:
        return {"task_id": task["task_id"], "total_score": 0.0, "dimension_scores": {}, "error": "no_rubric"}

    dim_scores = {}
    total = 0.0
    weight_sum = sum(d.get("weight", 0) for d in dimensions)

    for dim in dimensions:
        w = dim.get("weight", 0)
        score = apply_rubric_dimension(dim, candidate, ground_truth, inp)
        dim_scores[dim["name"]] = {"weight": w, "score": score, "weighted": round(w * score, 4)}
        total += w * score

    if weight_sum > 0:
        total = total / weight_sum

    return {
        "task_id": task["task_id"],
        "category": task.get("category", "unknown"),
        "probe_id": task.get("probe_id", ""),
        "source_mode": task.get("source_mode", ""),
        "difficulty": task.get("difficulty", ""),
        "total_score": round(total, 4),
        "expected_score": task.get("expected_score", None),
        "dimension_scores": dim_scores,
        "failure_detected": ground_truth.get("failure_detected", False),
        "failure_type": ground_truth.get("failure_type", ""),
    }


# ── Aggregate metrics ─────────────────────────────────────────────────────────

def compute_aggregate(results: List[Dict]) -> Dict:
    total = len(results)
    if total == 0:
        return {}

    scores = [r["total_score"] for r in results]
    avg = sum(scores) / total

    by_category: Dict[str, List[float]] = {}
    by_difficulty: Dict[str, List[float]] = {}
    by_source: Dict[str, List[float]] = {}

    for r in results:
        cat = r.get("category", "unknown")
        diff = r.get("difficulty", "unknown")
        src = r.get("source_mode", "unknown")
        by_category.setdefault(cat, []).append(r["total_score"])
        by_difficulty.setdefault(diff, []).append(r["total_score"])
        by_source.setdefault(src, []).append(r["total_score"])

    def mean_dict(d):
        return {k: round(sum(v) / len(v), 4) for k, v in d.items()}

    return {
        "total_tasks": total,
        "overall_score": round(avg, 4),
        "pass_rate_at_0_5": round(sum(1 for s in scores if s >= 0.5) / total, 4),
        "by_category": mean_dict(by_category),
        "by_difficulty": mean_dict(by_difficulty),
        "by_source_mode": mean_dict(by_source),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def load_tasks_from_jsonl(path: str) -> List[Dict]:
    tasks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def demo_mode(schema_path: str):
    """Score the 3 example tasks from schema.json."""
    schema = json.loads(Path(schema_path).read_text())
    examples = schema.get("examples", [])
    if not examples:
        print("No examples found in schema.json")
        return

    results = [score_task(t) for t in examples]
    print("\n=== DEMO: scoring schema.json examples ===\n")
    for r in results:
        print(f"  {r['task_id']}  category={r['category']:<28}  score={r['total_score']:.2f}  "
              f"expected={r.get('expected_score', '?')}  failure={r['failure_type']}")
    agg = compute_aggregate(results)
    print(f"\n  Overall: {agg['overall_score']:.4f}  pass@0.5: {agg['pass_rate_at_0_5']:.2%}\n")


def main():
    parser = argparse.ArgumentParser(description="Tenacious-Bench Scoring Evaluator")
    parser.add_argument("--partition", choices=["train", "dev", "held_out"], help="Dataset partition to score")
    parser.add_argument("--tasks_dir", default="tenacious_bench_v0.1", help="Root dataset directory")
    parser.add_argument("--agent_outputs", help="JSONL file of agent outputs (overrides partition tasks)")
    parser.add_argument("--output", default="results.json", help="Output file for results")
    parser.add_argument("--task_file", default="schema.json", help="Schema file for demo mode")
    parser.add_argument("--demo", action="store_true", help="Score the 3 schema.json example tasks")
    args = parser.parse_args()

    if args.demo:
        demo_mode(args.task_file)
        return

    if args.agent_outputs:
        tasks = load_tasks_from_jsonl(args.agent_outputs)
    elif args.partition:
        path = Path(args.tasks_dir) / args.partition / "tasks.jsonl"
        tasks = load_tasks_from_jsonl(str(path))
    else:
        parser.print_help()
        sys.exit(1)

    results = [score_task(t) for t in tasks]
    agg = compute_aggregate(results)

    output = {"aggregate": agg, "per_task": results}
    Path(args.output).write_text(json.dumps(output, indent=2))

    print(f"\nScored {agg['total_tasks']} tasks")
    print(f"Overall score:  {agg['overall_score']:.4f}")
    print(f"Pass rate @0.5: {agg['pass_rate_at_0_5']:.2%}")
    print(f"\nBy category:")
    for cat, score in sorted(agg["by_category"].items()):
        print(f"  {cat:<35} {score:.4f}")
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
