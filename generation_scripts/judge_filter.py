#!/usr/bin/env python3
"""
Tenacious-Bench v0.1 — Judge Quality Filter

Modes:
  1. Pointwise (default): Score each task on three dimensions (1–5).
       - input_coherence          : prospect fields are internally consistent
       - ground_truth_verifiability: ground truth can be verified by a script
       - rubric_clarity           : rubric dimensions are clear and implement-able
     Tasks with mean score >= 4.0 pass.

  2. Pairwise (--pairwise): Compare two candidate outputs for the same task.
     Given JSONL files A and B (matched by task_id), report which output is
     better according to the scoring rubric and by how much. Used to:
       - Validate chosen > rejected in preference datasets
       - Compare model variants (baseline vs trained)
       - Construct DPO/preference pairs from SFT-format data

Runs in heuristic mode (no API calls) by default; pass --llm to call an
Anthropic model for richer judgments.

Run:
  cd "tenacious bench"
  # Pointwise
  python generation_scripts/judge_filter.py --partition train
  python generation_scripts/judge_filter.py --partition dev --report judge_report.json
  python generation_scripts/judge_filter.py --input tasks.jsonl --output filtered.jsonl
  python generation_scripts/judge_filter.py --partition held_out --llm --model claude-haiku-4-5-20251001

  # Pairwise
  python generation_scripts/judge_filter.py --pairwise \\
      --input_a ablations/baseline_outputs.jsonl \\
      --input_b ablations/trained_outputs.jsonl \\
      --report pairwise_report.json

  # Generate preference pairs (adds 'rejected' field from injected failures)
  python generation_scripts/judge_filter.py --generate-pairs \\
      --input training_data/preferences_train.jsonl \\
      --output training_data/dpo_pairs_train.jsonl
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).parent.parent
BENCH_DIR = ROOT / "tenacious_bench_v0.1"
PASS_THRESHOLD = 4.0


def read_jsonl(path: Path) -> List[Dict]:
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def write_jsonl(path: Path, tasks: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")


# ── Heuristic scoring ─────────────────────────────────────────────────────────

def _score_input_coherence(task: Dict) -> Tuple[float, List[str]]:
    inp = task.get("input", {})
    issues: List[str] = []
    score = 5.0

    if not inp.get("prospect_domain"):
        issues.append("missing prospect_domain")
        score -= 2.0
    if not inp.get("prospect_name"):
        issues.append("missing prospect_name")
        score -= 1.0
    if inp.get("prospect_timezone") is None:
        issues.append("missing prospect_timezone")
        score -= 0.5
    if inp.get("bench_available") is None:
        issues.append("missing bench_available")
        score -= 0.5

    cb = inp.get("crunchbase_signal", {})
    cb_conf = cb.get("confidence", 0.0)
    if cb_conf > 0 and not cb.get("funding_stage"):
        issues.append("crunchbase confidence > 0 but no funding_stage")
        score -= 0.5
    if cb.get("recently_funded") and cb_conf == 0.0:
        issues.append("recently_funded=True but confidence=0.0")
        score -= 1.0

    cand = task.get("candidate_output", {})
    if "segment_assigned" not in cand:
        issues.append("candidate_output missing segment_assigned")
        score -= 1.0

    return max(1.0, score), issues


def _score_ground_truth_verifiability(task: Dict) -> Tuple[float, List[str]]:
    gt = task.get("ground_truth", {})
    issues: List[str] = []
    score = 5.0

    if "correct_segment" not in gt:
        issues.append("missing correct_segment")
        score -= 2.0
    else:
        seg = gt["correct_segment"]
        if seg not in (-1, 0, 1, 2, 3):
            issues.append(f"correct_segment={seg} not in {{-1,0,1,2,3}}")
            score -= 1.0

    if "failure_detected" not in gt:
        issues.append("missing failure_detected flag")
        score -= 1.0

    if not gt.get("failure_type"):
        issues.append("missing failure_type")
        score -= 0.5

    exp = task.get("expected_score")
    if exp is None:
        issues.append("missing expected_score")
        score -= 1.0
    elif not (0.0 <= float(exp) <= 1.0):
        issues.append(f"expected_score={exp} not in [0, 1]")
        score -= 1.0

    return max(1.0, score), issues


def _score_rubric_clarity(task: Dict) -> Tuple[float, List[str]]:
    rubric = task.get("scoring_rubric", {})
    dims   = rubric.get("dimensions", [])
    issues: List[str] = []
    score = 5.0

    if not dims:
        return 1.0, ["no rubric dimensions"]

    weight_sum = sum(d.get("weight", 0.0) for d in dims)
    if abs(weight_sum - 1.0) > 0.01:
        issues.append(f"weights sum to {weight_sum:.3f} (expected 1.0)")
        score -= 1.0

    for dim in dims:
        name = dim.get("name") or ""
        if not name:
            issues.append("dimension missing name")
            score -= 0.5
        if dim.get("weight", 0.0) <= 0:
            issues.append(f"dimension '{name}' has non-positive weight")
            score -= 0.5
        if not dim.get("check_expression"):
            issues.append(f"dimension '{name}' missing check_expression")
            score -= 0.5
        if not dim.get("description"):
            issues.append(f"dimension '{name}' missing description")
            score -= 0.25

    return max(1.0, score), issues


def heuristic_judge(task: Dict) -> Dict:
    ic_score,  ic_issues  = _score_input_coherence(task)
    gtv_score, gtv_issues = _score_ground_truth_verifiability(task)
    rc_score,  rc_issues  = _score_rubric_clarity(task)

    mean = (ic_score + gtv_score + rc_score) / 3.0

    return {
        "task_id": task["task_id"],
        "input_coherence": round(ic_score, 2),
        "ground_truth_verifiability": round(gtv_score, 2),
        "rubric_clarity": round(rc_score, 2),
        "mean_score": round(mean, 2),
        "passed": mean >= PASS_THRESHOLD,
        "mode": "heuristic",
        "issues": {
            "input_coherence": ic_issues,
            "ground_truth_verifiability": gtv_issues,
            "rubric_clarity": rc_issues,
        },
    }


# ── LLM judge mode ────────────────────────────────────────────────────────────

_JUDGE_PROMPT = """\
You are a quality judge for an evaluation benchmark dataset.

Score this benchmark task on three dimensions from 1 (very poor) to 5 (excellent):

1. input_coherence — Are the prospect input fields internally consistent? \
Do signal confidence levels align with presence of signals? Are required fields present?

2. ground_truth_verifiability — Can the ground truth be deterministically verified by a \
script? Is correct_segment clearly defined? Is failure_type specific enough to check?

3. rubric_clarity — Are the rubric dimensions specific and implementable? Do weights sum \
to 1.0? Are check_expressions unambiguous?

Task JSON:
{task_json}

Respond ONLY with valid JSON (no markdown):
{{"input_coherence": <1-5>, "ground_truth_verifiability": <1-5>, \
"rubric_clarity": <1-5>, "issues": "<brief description or 'none'>"}}"""


def llm_judge(task: Dict, model: str = "claude-haiku-4-5-20251001") -> Dict:
    try:
        import anthropic
    except ImportError:
        print("anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic()
    prompt = _JUDGE_PROMPT.format(
        task_json=json.dumps(task, indent=2, ensure_ascii=False)[:4000]
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        scores = json.loads(response.content[0].text.strip())
    except Exception as exc:
        print(f"  LLM judge error for {task.get('task_id')}: {exc} — falling back to heuristic")
        return heuristic_judge(task)

    ic  = float(scores.get("input_coherence", 3))
    gtv = float(scores.get("ground_truth_verifiability", 3))
    rc  = float(scores.get("rubric_clarity", 3))
    mean = (ic + gtv + rc) / 3.0

    return {
        "task_id": task["task_id"],
        "input_coherence": ic,
        "ground_truth_verifiability": gtv,
        "rubric_clarity": rc,
        "mean_score": round(mean, 2),
        "passed": mean >= PASS_THRESHOLD,
        "mode": "llm",
        "issues": {"llm_notes": scores.get("issues", "")},
    }


# ── Pairwise comparison ───────────────────────────────────────────────────────

import sys as _sys
_ROOT_FOR_SCORER = Path(__file__).parent.parent
_sys.path.insert(0, str(_ROOT_FOR_SCORER))


def _score_candidate(task: Dict, candidate_output: Dict) -> float:
    """Score a single candidate_output against a task's rubric. Returns 0.0–1.0."""
    try:
        from scoring_evaluator import score_task as _score_task
        patched = {**task, "candidate_output": candidate_output}
        return _score_task(patched)["total_score"]
    except Exception:
        return 0.0


def pairwise_compare(
    tasks_by_id: Dict[str, Dict],
    outputs_a: Dict[str, Dict],
    outputs_b: Dict[str, Dict],
    label_a: str = "A",
    label_b: str = "B",
) -> Dict:
    """
    Compare two sets of candidate outputs on the same tasks using the scoring rubric.
    Returns per-task winner decisions and aggregate win rates.
    """
    per_task = []
    a_wins = b_wins = ties = 0

    for task_id, task in sorted(tasks_by_id.items()):
        if task_id not in outputs_a or task_id not in outputs_b:
            continue
        score_a = _score_candidate(task, outputs_a[task_id])
        score_b = _score_candidate(task, outputs_b[task_id])
        delta = round(score_a - score_b, 4)

        if delta > 0.05:
            winner = label_a
            a_wins += 1
        elif delta < -0.05:
            winner = label_b
            b_wins += 1
        else:
            winner = "tie"
            ties += 1

        per_task.append({
            "task_id": task_id,
            "category": task.get("category", ""),
            f"score_{label_a}": round(score_a, 4),
            f"score_{label_b}": round(score_b, 4),
            "delta_a_minus_b": delta,
            "winner": winner,
        })

    n = len(per_task)
    return {
        "n_compared": n,
        "label_a": label_a,
        "label_b": label_b,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "a_win_rate": round(a_wins / n * 100, 1) if n else 0.0,
        "b_win_rate": round(b_wins / n * 100, 1) if n else 0.0,
        "mean_score_a": round(sum(r[f"score_{label_a}"] for r in per_task) / n, 4) if n else 0.0,
        "mean_score_b": round(sum(r[f"score_{label_b}"] for r in per_task) / n, 4) if n else 0.0,
        "per_task": per_task,
    }


# ── Failure injection for preference pair generation ──────────────────────────

_INJECTED_BANNED = ["leverage", "world-class", "game-changer", "synergy"]


def _inject_failure(chosen_text: str, category: str) -> str:
    """Produce a 'rejected' variant by injecting known failure patterns into chosen."""
    if category in ("tone_drift", "icp_misclassification"):
        return chosen_text + "\n\nOur world-class, game-changer platform can leverage synergy for you."
    if category in ("bench_over_commitment",):
        return chosen_text.replace(
            "we'd scope headcount together on a call",
            "we can deploy a 10-person team within two weeks",
        ) if "scope headcount" in chosen_text else (
            chosen_text + "\n\nWe can staff 10 engineers within 2 weeks."
        )
    if category in ("hiring_signal_over_claiming",):
        return chosen_text + "\n\nYour team is clearly scaling rapidly — don't miss out."
    # Generic fallback: add three banned phrases to guarantee rubric failure
    return chosen_text + f"\n\nWe offer {_INJECTED_BANNED[0]} and {_INJECTED_BANNED[1]} solutions."


def generate_preference_pairs(sft_records: List[Dict]) -> List[Dict]:
    """
    Transform SFT-format records (chosen only) into DPO preference pairs by
    injecting rubric-violating failures into each chosen to produce a rejected.

    Output format per record:
      { system, prompt, chosen, rejected, task_id, category, ... }
    """
    pairs = []
    for rec in sft_records:
        chosen = rec.get("chosen", "")
        category = rec.get("category", "")
        rejected = _inject_failure(chosen, category)
        pairs.append({**rec, "rejected": rejected})
    return pairs


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Tenacious-Bench judge quality filter")

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--partition", choices=["train", "dev", "held_out"],
                            help="Pointwise: partition to filter")
    mode_group.add_argument("--input", type=Path,
                            help="Pointwise: input JSONL file path")
    mode_group.add_argument("--pairwise", action="store_true",
                            help="Pairwise mode: compare --input_a vs --input_b")
    mode_group.add_argument("--generate-pairs", action="store_true", dest="generate_pairs",
                            help="Generate DPO preference pairs from SFT-format chosen-only JSONL")

    # Pointwise options
    parser.add_argument("--output", type=Path, default=None,
                        help="Output filtered JSONL (default: <input_stem>_filtered.jsonl)")
    parser.add_argument("--llm", action="store_true",
                        help="Use Anthropic LLM judge instead of heuristic")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001",
                        help="Anthropic model ID for --llm mode")
    parser.add_argument("--report", type=Path, default=None,
                        help="Save per-task judgment report JSON")

    # Pairwise options
    parser.add_argument("--input_a", type=Path, default=None,
                        help="Pairwise: JSONL with candidate_outputs for condition A")
    parser.add_argument("--input_b", type=Path, default=None,
                        help="Pairwise: JSONL with candidate_outputs for condition B")
    parser.add_argument("--label_a", default="baseline",
                        help="Pairwise: label for condition A (default: baseline)")
    parser.add_argument("--label_b", default="trained",
                        help="Pairwise: label for condition B (default: trained)")
    parser.add_argument("--tasks_jsonl", type=Path, default=None,
                        help="Pairwise: tasks JSONL providing ground truth and rubrics")

    args = parser.parse_args()

    # ── Generate preference pairs ─────────────────────────────────────────────
    if args.generate_pairs:
        if not args.input or not args.input.exists():
            print("ERROR: --generate-pairs requires --input <sft_format.jsonl>")
            sys.exit(1)
        records = read_jsonl(args.input)
        pairs = generate_preference_pairs(records)
        out_path = args.output or args.input.parent / (args.input.stem + "_dpo.jsonl")
        write_jsonl(out_path, pairs)
        chosen_cnt = sum(1 for r in pairs if r.get("chosen"))
        rejected_cnt = sum(1 for r in pairs if r.get("rejected"))
        print(f"Generated {len(pairs)} DPO pairs → {out_path}")
        print(f"  chosen fields: {chosen_cnt}  rejected fields: {rejected_cnt}")
        return

    # ── Pairwise comparison ───────────────────────────────────────────────────
    if args.pairwise:
        if not args.input_a or not args.input_b:
            print("ERROR: --pairwise requires --input_a and --input_b")
            sys.exit(1)
        for p, label in [(args.input_a, "input_a"), (args.input_b, "input_b")]:
            if not p.exists():
                print(f"ERROR: {label} not found: {p}")
                sys.exit(1)

        tasks_path = args.tasks_jsonl or BENCH_DIR / "held_out" / "tasks.jsonl"
        if not tasks_path.exists():
            tasks_path = BENCH_DIR / "dev" / "tasks.jsonl"
        tasks_list = read_jsonl(tasks_path)
        tasks_by_id = {t["task_id"]: t for t in tasks_list}

        def _load_outputs(path: Path) -> Dict[str, Dict]:
            outputs: Dict[str, Dict] = {}
            for rec in read_jsonl(path):
                tid = rec.get("task_id")
                if tid:
                    outputs[tid] = rec.get("candidate_output", rec)
            return outputs

        outputs_a = _load_outputs(args.input_a)
        outputs_b = _load_outputs(args.input_b)

        print(f"Comparing {len(outputs_a)} outputs from A ({args.label_a}) "
              f"vs {len(outputs_b)} outputs from B ({args.label_b})...")
        result = pairwise_compare(tasks_by_id, outputs_a, outputs_b,
                                  label_a=args.label_a, label_b=args.label_b)

        print(f"\n{'='*55}")
        print(f"Pairwise judge result  ({result['n_compared']} matched pairs)")
        print(f"{'='*55}")
        print(f"  {args.label_a} wins : {result['a_wins']:3d}  ({result['a_win_rate']:.1f}%)")
        print(f"  {args.label_b} wins : {result['b_wins']:3d}  ({result['b_win_rate']:.1f}%)")
        print(f"  Ties        : {result['ties']:3d}")
        print(f"  Mean score {args.label_a}: {result['mean_score_a']:.4f}")
        print(f"  Mean score {args.label_b}: {result['mean_score_b']:.4f}")
        print(f"  Delta (A-B) : {result['mean_score_a'] - result['mean_score_b']:+.4f}")
        print(f"{'='*55}")

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"  Pairwise report: {args.report}")
        return

    # ── Pointwise ─────────────────────────────────────────────────────────────
    in_path = (BENCH_DIR / args.partition / "tasks.jsonl") if args.partition else args.input
    if not in_path.exists():
        print(f"ERROR: {in_path} not found")
        sys.exit(1)

    tasks = read_jsonl(in_path)
    print(f"Loaded {len(tasks)} tasks from {in_path}")

    mode_label = "LLM" if args.llm else "heuristic"
    print(f"Judging in {mode_label} mode (pass threshold >= {PASS_THRESHOLD}/5)...")

    judgments: List[Dict] = []
    passed_tasks: List[Dict] = []
    failed_tasks: List[Dict] = []

    for i, task in enumerate(tasks):
        j = llm_judge(task, model=args.model) if args.llm else heuristic_judge(task)
        judgments.append(j)
        if j["passed"]:
            passed_tasks.append(task)
        else:
            failed_tasks.append(task)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(tasks)} judged...")

    pass_rate = len(passed_tasks) / len(tasks) * 100
    print(f"\nResults: {len(passed_tasks)}/{len(tasks)} passed ({pass_rate:.1f}%)")
    if failed_tasks:
        print("  Failed:", [t["task_id"] for t in failed_tasks[:10]])

    out_path = args.output or in_path.parent / (in_path.stem + "_filtered.jsonl")
    write_jsonl(out_path, passed_tasks)
    print(f"  Filtered dataset: {out_path}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": {
                        "total": len(tasks),
                        "passed": len(passed_tasks),
                        "failed": len(failed_tasks),
                        "pass_rate": round(pass_rate, 2),
                        "mode": mode_label,
                        "threshold": PASS_THRESHOLD,
                    },
                    "per_task": judgments,
                },
                f,
                indent=2,
            )
        print(f"  Judgment report: {args.report}")


if __name__ == "__main__":
    main()
