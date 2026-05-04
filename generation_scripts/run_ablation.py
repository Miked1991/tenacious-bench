#!/usr/bin/env python3
"""
Tenacious-Bench v0.1 — Ablation Runner (generation_scripts version)

Produces the root-level ablation_results.json and statistical_test_output.txt
using Wilcoxon signed-rank test + paired bootstrap CI (no scipy dependency).

Run:
  cd "tenacious bench"

  # Score baseline only (uses candidate_output embedded in tasks.jsonl)
  python generation_scripts/run_ablation.py

  # Full Delta A: supply trained model outputs
  python generation_scripts/run_ablation.py \\
      --trained_outputs ablations/trained_outputs.jsonl

  # Full Delta A + B (prompt-engineered control)
  python generation_scripts/run_ablation.py \\
      --trained_outputs ablations/trained_outputs.jsonl \\
      --prompted_outputs ablations/prompted_outputs.jsonl

Outputs:
  ablation_results.json         — summary + per-category table (root level)
  statistical_test_output.txt   — human-readable test report (root level)
"""

import json
import math
import argparse
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

HELD_OUT_PATH = ROOT / "tenacious_bench_v0.1" / "held_out" / "tasks.jsonl"
SEED = 42
BOOTSTRAP_N = 10_000


# ── I/O ───────────────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> List[Dict]:
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def load_outputs(path: Path) -> Dict[str, Dict]:
    """Load JSONL keyed by task_id → candidate_output."""
    outputs: Dict[str, Dict] = {}
    for item in read_jsonl(path):
        tid = item.get("task_id")
        if tid:
            outputs[tid] = item.get("candidate_output", item)
    return outputs


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_condition(tasks: List[Dict], overrides: Optional[Dict[str, Dict]] = None) -> List[float]:
    scores = []
    for task in tasks:
        if overrides and task["task_id"] in overrides:
            task = {**task, "candidate_output": overrides[task["task_id"]]}
        scores.append(score_task(task)["total_score"])
    return scores


def category_means(tasks: List[Dict], scores: List[float]) -> Dict[str, Dict]:
    by_cat: Dict[str, List[float]] = {}
    for task, score in zip(tasks, scores):
        by_cat.setdefault(task.get("category", "unknown"), []).append(score)
    return {
        cat: {"n": len(v), "mean": round(sum(v) / len(v) * 100, 1)}
        for cat, v in sorted(by_cat.items())
    }


def category_bootstrap_ci(
    tasks: List[Dict],
    scores: List[float],
    n_iter: int = BOOTSTRAP_N,
) -> Dict[str, Tuple[float, float]]:
    """95% bootstrap CI on the mean score for each category.

    Categories with n < 6 have wide CIs and should be interpreted
    as directional only (±30pp or more at n=4).
    """
    by_cat: Dict[str, List[float]] = {}
    for task, score in zip(tasks, scores):
        by_cat.setdefault(task.get("category", "unknown"), []).append(score)

    rng = random.Random(SEED)
    result: Dict[str, Tuple[float, float]] = {}
    for cat, cat_scores in sorted(by_cat.items()):
        n = len(cat_scores)
        boot = []
        for _ in range(n_iter):
            sample = [rng.choice(cat_scores) for _ in range(n)]
            boot.append(sum(sample) / n * 100)
        boot.sort()
        lo = boot[int(0.025 * n_iter)]
        hi = boot[int(0.975 * n_iter)]
        result[cat] = (round(lo, 1), round(hi, 1))
    return result


# ── Statistics ────────────────────────────────────────────────────────────────

def _normal_sf(z: float) -> float:
    """P(Z > z) — Abramowitz & Stegun 26.2.17."""
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = t * (0.319381530
                + t * (-0.356563782
                + t * (1.781477937
                + t * (-1.821255978
                + t * 1.330274429))))
    p = (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return p if z >= 0 else 1.0 - p


def wilcoxon_signed_rank(a: List[float], b: List[float]) -> Tuple[float, bool]:
    """Two-sided Wilcoxon signed-rank p-value (normal approximation). Returns (p, significant)."""
    diffs = [x - y for x, y in zip(a, b) if x != y]
    if not diffs:
        return 1.0, False
    ranks = sorted(range(len(diffs)), key=lambda i: abs(diffs[i]))
    w_plus = sum(r + 1 for r in range(len(diffs)) if diffs[ranks[r]] > 0)
    n = len(diffs)
    mean_w = n * (n + 1) / 4
    std_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w_plus - mean_w) / std_w if std_w > 0 else 0.0
    p = 2 * _normal_sf(abs(z))
    return round(p, 6), p < 0.05


def bootstrap_ci(a: List[float], b: List[float], n_iter: int = BOOTSTRAP_N) -> Tuple[float, float]:
    """95% paired bootstrap CI on mean(a) - mean(b) in percentage points."""
    rng = random.Random(SEED)
    diffs = [x - y for x, y in zip(a, b)]
    n = len(diffs)
    boot_deltas = []
    for _ in range(n_iter):
        sample = [rng.choice(diffs) for _ in range(n)]
        boot_deltas.append(sum(sample) / n * 100)
    boot_deltas.sort()
    lo = boot_deltas[int(0.025 * n_iter)]
    hi = boot_deltas[int(0.975 * n_iter)]
    return round(lo, 1), round(hi, 1)


# ── Report ────────────────────────────────────────────────────────────────────

def _text_report(
    n: int,
    base_mean: float,
    trained_mean: float,
    delta: float,
    ci: Tuple[float, float],
    p: float,
    sig: bool,
    cat_base: Dict,
    cat_trained: Dict,
    ts: str,
) -> str:
    lines = [
        "Tenacious-Bench SFT — Ablation Statistical Test",
        f"Run: {ts}",
        "=" * 55,
        "Test: Wilcoxon signed-rank (two-sided) + bootstrap CI",
        f"N = {n}  |  bootstrap iterations = {BOOTSTRAP_N:,}  |  seed={SEED}",
        "-" * 55,
        f"Baseline mean  : {base_mean:.1f}%",
        f"Trained mean   : {trained_mean:.1f}%",
        f"Delta A        : {delta:+.1f} pp",
        f"95% CI (delta) : [{ci[0]}, {ci[1]}] pp",
        f"p-value        : {p:.6f}",
        f"Significant    : {'YES' if sig else 'NO'}",
        "=" * 55,
    ]
    if cat_trained:
        lines.append("")
        lines.append("Per-category breakdown (baseline → trained, 95% CI, n tasks):")
        lines.append("  ⚠ Categories with n<6 have wide CIs — treat as directional only.")
        for cat in sorted(set(cat_base) | set(cat_trained)):
            b = cat_base.get(cat, {})
            t = cat_trained.get(cat, {})
            bm = b.get("mean", 0.0)
            tm = t.get("mean", 0.0)
            nb = b.get("n", 0)
            warn = " ⚠ low-n" if nb < 6 else ""
            lines.append(f"  {cat:<35}: {bm:5.1f}% → {tm:5.1f}%  ({tm - bm:+.1f}pp, n={nb}){warn}")
        lines.append("=" * 55)
    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Tenacious-Bench ablation runner")
    parser.add_argument("--held_out", type=Path, default=HELD_OUT_PATH)
    parser.add_argument("--trained_outputs", type=Path, default=None,
                        help="Trained model outputs JSONL (for Delta A)")
    parser.add_argument("--prompted_outputs", type=Path, default=None,
                        help="Prompt-engineered control outputs JSONL (for Delta B)")
    parser.add_argument("--output_json", type=Path, default=ROOT / "ablation_results.json")
    parser.add_argument("--output_txt", type=Path, default=ROOT / "statistical_test_output.txt")
    args = parser.parse_args()

    if not args.held_out.exists():
        print(f"ERROR: {args.held_out} not found")
        sys.exit(1)

    tasks = read_jsonl(args.held_out)
    n = len(tasks)
    ts = datetime.now().isoformat()
    print(f"Loaded {n} held-out tasks from {args.held_out}")

    # Baseline
    print("Scoring baseline...")
    base_scores = score_condition(tasks)
    base_mean = sum(base_scores) / n * 100
    cat_base = category_means(tasks, base_scores)
    print(f"  Baseline: {base_mean:.1f}%")

    # Trained
    trained_scores: Optional[List[float]] = None
    trained_mean = 0.0
    cat_trained: Dict = {}
    delta = p = ci = None
    sig = False

    if args.trained_outputs:
        if not args.trained_outputs.exists():
            print(f"ERROR: --trained_outputs not found: {args.trained_outputs}")
            sys.exit(1)
        overrides = load_outputs(args.trained_outputs)
        print(f"Scoring trained model ({len(overrides)} outputs)...")
        trained_scores = score_condition(tasks, overrides)
        trained_mean = sum(trained_scores) / n * 100
        cat_trained = category_means(tasks, trained_scores)
        delta = round(trained_mean - base_mean, 1)
        p, sig = wilcoxon_signed_rank(trained_scores, base_scores)
        ci = bootstrap_ci(trained_scores, base_scores)
        print(f"  Trained: {trained_mean:.1f}%")
        print(f"  Delta A: {delta:+.1f} pp | p={p:.6f} | 95% CI [{ci[0]}, {ci[1]}]")
    else:
        print("No --trained_outputs. Reporting baseline only.")

    # Per-category CIs (Gap 5 fix: small n categories have wide uncertainty)
    base_cat_ci    = category_bootstrap_ci(tasks, base_scores)
    trained_cat_ci = category_bootstrap_ci(tasks, trained_scores) if trained_scores else {}

    # Per-category table
    per_category = []
    for cat in sorted(set(cat_base) | set(cat_trained)):
        n_tasks = cat_base.get(cat, {}).get("n", cat_trained.get(cat, {}).get("n", 0))
        b_ci = base_cat_ci.get(cat, (0.0, 0.0))
        t_ci = trained_cat_ci.get(cat, (0.0, 0.0))
        entry: Dict = {
            "category": cat,
            "n": n_tasks,
            "baseline": cat_base.get(cat, {}).get("mean", 0.0),
            "baseline_ci_95": list(b_ci),
            "trained": cat_trained.get(cat, {}).get("mean", 0.0),
            "trained_ci_95": list(t_ci),
            "delta_pp": round(
                cat_trained.get(cat, {}).get("mean", 0.0) - cat_base.get(cat, {}).get("mean", 0.0), 1
            ),
            "low_n_warning": n_tasks < 6,
        }
        per_category.append(entry)

    # Build JSON output
    result: Dict = {
        "run_timestamp": ts,
        "model": "unsloth/Qwen3-4B-bnb-4bit",
        "adapter": "mike-D83/tenacious-bench-sft-adapter-v0.1",
        "held_out_n": n,
        "baseline_mean": round(base_mean, 1),
        "trained_mean": round(trained_mean, 1) if trained_scores else None,
        "delta_a_pp": delta,
        "ci_95": list(ci) if ci else None,
        "p_value": p,
        "significant": sig,
        "test": f"Wilcoxon signed-rank two-sided + paired bootstrap CI (n={BOOTSTRAP_N:,}, seed={SEED})",
        "per_category": per_category,
    }

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults: {args.output_json}")

    # Build text report
    txt = _text_report(
        n=n,
        base_mean=base_mean,
        trained_mean=trained_mean,
        delta=delta or 0.0,
        ci=ci or (0.0, 0.0),
        p=p or 1.0,
        sig=sig,
        cat_base=cat_base,
        cat_trained=cat_trained,
        ts=ts,
    )
    with open(args.output_txt, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"Text report: {args.output_txt}")
    print(txt)


if __name__ == "__main__":
    main()
