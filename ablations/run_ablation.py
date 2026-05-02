#!/usr/bin/env python3
"""
Tenacious-Bench v0.1 — Ablation Harness

Compares three conditions on the held-out partition and reports:
  - Delta A: Trained LoRA vs Week 10 baseline
  - Delta B: Trained LoRA vs prompt-engineered control (optional)
  - Delta C: Effect on tau2-Bench retail score (optional)

Statistical test: McNemar's test (paired binary pass/fail per task).

Run:
  cd "tenacious bench"

  # Score baseline only (uses candidate_output from tasks.jsonl)
  python ablations/run_ablation.py

  # Full Delta A comparison
  python ablations/run_ablation.py \\
      --trained_outputs ablations/trained_outputs.jsonl

  # All three deltas
  python ablations/run_ablation.py \\
      --trained_outputs  ablations/trained_outputs.jsonl \\
      --prompted_outputs ablations/prompted_outputs.jsonl \\
      --tau2_trained 73.1

Output files:
  ablations/ablation_results.json   — summary + per-category table
  ablations/held_out_traces.jsonl   — per-task scores for all conditions
"""

import json
import math
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

HELD_OUT_PATH = ROOT / "tenacious_bench_v0.1" / "held_out" / "tasks.jsonl"
PASS_THRESHOLD = 0.5  # score >= 0.5 counts as pass


# ── I/O helpers ───────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> List[Dict]:
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def load_agent_outputs(path: Path) -> Dict[str, Dict]:
    """Load JSONL keyed by task_id, expecting {task_id, candidate_output} rows."""
    outputs: Dict[str, Dict] = {}
    for item in read_jsonl(path):
        tid = item.get("task_id")
        if tid:
            outputs[tid] = item.get("candidate_output", item)
    return outputs


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_condition(
    tasks: List[Dict], overrides: Optional[Dict[str, Dict]] = None
) -> List[Dict]:
    """
    Score all tasks. If overrides is provided, each task whose task_id appears in
    overrides has its candidate_output replaced before scoring.
    """
    results = []
    for task in tasks:
        if overrides and task["task_id"] in overrides:
            task = {**task, "candidate_output": overrides[task["task_id"]]}
        r = score_task(task)
        r["passed"] = r["total_score"] >= PASS_THRESHOLD
        results.append(r)
    return results


def pass_rate(results: List[Dict]) -> float:
    return sum(1 for r in results if r["passed"]) / len(results) * 100


def category_pass_rates(results: List[Dict]) -> Dict[str, Dict]:
    by_cat: Dict[str, List[bool]] = {}
    for r in results:
        cat = r.get("category", "unknown")
        by_cat.setdefault(cat, []).append(r["passed"])
    return {
        cat: {
            "n": len(v),
            "passed": int(sum(v)),
            "pass_rate": round(sum(v) / len(v) * 100, 1),
        }
        for cat, v in sorted(by_cat.items())
    }


# ── Statistics ────────────────────────────────────────────────────────────────

def mcnemar_test(a_results: List[Dict], b_results: List[Dict]) -> Dict:
    """
    McNemar's test (with continuity correction) for paired pass/fail.
    H0: P(A passes, B fails) == P(A fails, B passes).
    """
    b_by_id = {r["task_id"]: r for r in b_results}
    n_ab = 0  # A pass, B fail
    n_ba = 0  # A fail, B pass

    for ra in a_results:
        rb = b_by_id.get(ra["task_id"])
        if rb is None:
            continue
        if ra["passed"] and not rb["passed"]:
            n_ab += 1
        elif not ra["passed"] and rb["passed"]:
            n_ba += 1

    n = n_ab + n_ba
    if n == 0:
        return {
            "n_discordant": 0, "chi2": 0.0, "p_value": 1.0, "significant": False,
            "note": "no discordant pairs — conditions produce identical pass/fail vectors",
        }

    chi2 = (abs(n_ab - n_ba) - 1) ** 2 / n
    p_value = _chi2_1df_sf(chi2)

    return {
        "n_discordant": n,
        "b_better_count": n_ba,
        "a_better_count": n_ab,
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 4),
        "significant": p_value < 0.05,
    }


def _chi2_1df_sf(x: float) -> float:
    """P(chi2_1 > x): survival function via normal approximation."""
    if x <= 0:
        return 1.0
    return 2 * _normal_sf(math.sqrt(x))


def _normal_sf(z: float) -> float:
    """P(Z > z) for standard normal (Abramowitz & Stegun 26.2.17)."""
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = t * (
        0.319381530
        + t * (-0.356563782
        + t * (1.781477937
        + t * (-1.821255978
        + t * 1.330274429)))
    )
    p = (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return p if z >= 0 else 1.0 - p


def ci_95(delta_pp: float, n: int) -> Tuple[float, float]:
    """95% CI for a percentage-point delta (normal approximation)."""
    if n == 0:
        return (0.0, 0.0)
    se = math.sqrt(abs(delta_pp) * (100 - abs(delta_pp)) / n)
    margin = 1.96 * se
    return (round(delta_pp - margin, 1), round(delta_pp + margin, 1))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Tenacious-Bench ablation harness")
    parser.add_argument("--held_out", type=Path, default=HELD_OUT_PATH,
                        help="Held-out tasks JSONL")
    parser.add_argument("--trained_outputs", type=Path, default=None,
                        help="Trained model candidate_outputs JSONL (for Delta A)")
    parser.add_argument("--prompted_outputs", type=Path, default=None,
                        help="Prompt-engineered control candidate_outputs JSONL (for Delta B)")
    parser.add_argument("--tau2_baseline", type=float, default=72.7,
                        help="Week 10 tau2-Bench retail score %%")
    parser.add_argument("--tau2_trained", type=float, default=None,
                        help="Trained model tau2-Bench retail score %% (for Delta C)")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "ablations" / "ablation_results.json")
    parser.add_argument("--traces", type=Path,
                        default=ROOT / "ablations" / "held_out_traces.jsonl")
    args = parser.parse_args()

    if not args.held_out.exists():
        print(f"ERROR: {args.held_out} not found")
        sys.exit(1)

    tasks = read_jsonl(args.held_out)
    n = len(tasks)
    print(f"Loaded {n} held-out tasks from {args.held_out}")

    # ── Baseline ──────────────────────────────────────────────────────────────
    print("\nScoring baseline (Week 10 agent — candidate_output in tasks.jsonl)...")
    baseline = score_condition(tasks)
    base_rate = pass_rate(baseline)
    print(f"  Baseline: {base_rate:.1f}% pass rate")

    # ── Trained ───────────────────────────────────────────────────────────────
    trained = None
    trained_rate = None
    if args.trained_outputs:
        if not args.trained_outputs.exists():
            print(f"ERROR: --trained_outputs not found: {args.trained_outputs}")
            sys.exit(1)
        overrides = load_agent_outputs(args.trained_outputs)
        print(f"\nScoring trained model ({len(overrides)} outputs from {args.trained_outputs})...")
        trained = score_condition(tasks, overrides=overrides)
        trained_rate = pass_rate(trained)
        print(f"  Trained: {trained_rate:.1f}% pass rate")
    else:
        print("\nNo --trained_outputs. Reporting baseline scores only.")

    # ── Prompted control ──────────────────────────────────────────────────────
    prompted = None
    prompted_rate = None
    if args.prompted_outputs:
        if not args.prompted_outputs.exists():
            print(f"ERROR: --prompted_outputs not found: {args.prompted_outputs}")
            sys.exit(1)
        overrides_p = load_agent_outputs(args.prompted_outputs)
        print(f"\nScoring prompted control ({len(overrides_p)} outputs)...")
        prompted = score_condition(tasks, overrides=overrides_p)
        prompted_rate = pass_rate(prompted)
        print(f"  Prompted: {prompted_rate:.1f}% pass rate")

    # ── Per-category breakdown ────────────────────────────────────────────────
    base_cats    = category_pass_rates(baseline)
    trained_cats = category_pass_rates(trained) if trained else {}

    per_category = []
    for cat, base in base_cats.items():
        entry: Dict = {
            "category": cat,
            "n": base["n"],
            "baseline_pass_rate": base["pass_rate"],
        }
        if cat in trained_cats:
            entry["trained_pass_rate"] = trained_cats[cat]["pass_rate"]
            entry["delta_a_pp"] = round(trained_cats[cat]["pass_rate"] - base["pass_rate"], 1)
        per_category.append(entry)

    # ── Delta A ───────────────────────────────────────────────────────────────
    delta_a = round(trained_rate - base_rate, 1) if trained_rate is not None else None
    stat_a  = mcnemar_test(baseline, trained) if trained else None
    ci_a    = ci_95(delta_a, n) if delta_a is not None else None

    if delta_a is not None:
        print(f"\nDelta A: {delta_a:+.1f} pp | p={stat_a['p_value']:.4f} | "
              f"95% CI [{ci_a[0]}, {ci_a[1]}]")
        if stat_a["significant"]:
            print("  Statistically significant (p < 0.05)")

    # ── Delta B ───────────────────────────────────────────────────────────────
    delta_b = (round(trained_rate - prompted_rate, 1)
               if (trained_rate is not None and prompted_rate is not None) else None)
    stat_b  = mcnemar_test(prompted, trained) if (prompted and trained) else None
    ci_b    = ci_95(delta_b, n) if delta_b is not None else None

    if delta_b is not None:
        print(f"Delta B: {delta_b:+.1f} pp | p={stat_b['p_value']:.4f} | "
              f"95% CI [{ci_b[0]}, {ci_b[1]}]")

    # ── Delta C ───────────────────────────────────────────────────────────────
    delta_c = (round(args.tau2_trained - args.tau2_baseline, 1)
               if args.tau2_trained is not None else None)
    if delta_c is not None:
        print(f"Delta C (tau2-Bench retail): {delta_c:+.1f} pp")

    # ── Assemble output ───────────────────────────────────────────────────────
    import datetime

    result: Dict = {
        "_description": "Tenacious-Bench v0.1 ablation results",
        "_generated": str(datetime.date.today()),
        "conditions": {
            "baseline": {
                "description": "Week 10 agent (candidate_output from tasks.jsonl)",
                "n_tasks": n,
                "score_pct": round(base_rate, 1),
            },
        },
        "per_category_baseline": base_cats,
        "per_category": per_category,
    }

    if trained:
        result["conditions"]["trained_lora"] = {
            "description": "LoRA adapter (unsloth/Qwen3-4B-bnb-4bit, r=8 alpha=16)",
            "n_tasks": n,
            "score_pct": round(trained_rate, 1),
        }

    if prompted:
        result["conditions"]["prompt_engineered"] = {
            "description": "Full Tenacious style guide in system prompt, no fine-tuning",
            "n_tasks": n,
            "score_pct": round(prompted_rate, 1),
        }

    deltas: Dict = {}
    if delta_a is not None:
        deltas["delta_a"] = {
            "description": "Trained LoRA vs Week 10 baseline",
            "value_pp": delta_a,
            "ci_95": list(ci_a),
            "p_value": stat_a["p_value"],
            "significant": stat_a["significant"],
            "mcnemar": stat_a,
        }
    if delta_b is not None:
        deltas["delta_b"] = {
            "description": "Trained LoRA vs prompt-engineered control",
            "value_pp": delta_b,
            "ci_95": list(ci_b),
            "p_value": stat_b["p_value"],
            "significant": stat_b["significant"],
            "mcnemar": stat_b,
        }
    if delta_c is not None:
        deltas["delta_c"] = {
            "description": "Effect on tau2-Bench retail (expected near-zero)",
            "tau2_baseline": args.tau2_baseline,
            "tau2_trained": args.tau2_trained,
            "value_pp": delta_c,
        }
    if deltas:
        result["deltas"] = deltas

    # ── Save results ──────────────────────────────────────────────────────────
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nAblation results: {args.output}")

    # ── Save traces ───────────────────────────────────────────────────────────
    args.traces.parent.mkdir(parents=True, exist_ok=True)
    with open(args.traces, "w", encoding="utf-8") as f:
        for i, task in enumerate(tasks):
            trace = {
                "task_id": task["task_id"],
                "category": task.get("category"),
                "baseline": baseline[i],
            }
            if trained:
                trace["trained"] = trained[i]
            if prompted:
                trace["prompted"] = prompted[i]
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")
    print(f"Held-out traces:   {args.traces}")


if __name__ == "__main__":
    main()
