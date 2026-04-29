# Tenacious-Bench v0.1

**Author:** Mikias Dagem | **Email:** mikias@10academy.org  
**Created:** 2026-04-29 | **Version:** 0.1 (Interim — Acts I & II)  
**License:** CC-BY-4.0

## Overview

Tenacious-Bench is a Tenacious-specific evaluation dataset for the Conversion Engine agent built in Week 10. It measures failure modes that τ²-Bench retail cannot grade: prospect segment misclassification, bench over-commitment, tone drift against the Tenacious style guide, hiring-signal over-claiming, multi-thread data leakage, scheduling timezone errors, and eight other categories derived from 36 documented probes.

**250 tasks** across 10 failure categories. Three partitions: training (50%), public dev (30%), sealed held-out (20%).

## Repository Structure

```
tenacious bench/
├── README.md                          # This file
├── audit_memo.md                      # 600-word gap analysis vs. τ²-Bench retail
├── schema.json                        # Task schema + 3 annotated examples
├── scoring_evaluator.py               # Machine-verifiable scorer (no human in loop)
├── methodology.md                     # Path A declaration, justification, partitioning
├── datasheet.md                       # Gebru + Pushkarna documentation
├── inter_rater_agreement.md           # 30-task self-agreement matrix
├── cost_log.md                        # Every API / compute charge logged
├── contamination_check.json           # N-gram, embedding, time-shift check results
├── .gitignore
├── tenacious_bench_v0.1/
│   ├── train/tasks.jsonl              # 125 tasks (50%) — training partition
│   ├── dev/tasks.jsonl                # 75 tasks (30%) — public dev partition
│   └── held_out/tasks.jsonl          # 50 tasks (20%) — sealed (gitignored)
├── generation_scripts/
│   ├── generate_dataset.py            # Reproducible generation (seed=42)
│   ├── contamination_check.py         # N-gram + embedding + time-shift checks
│   └── judge_filter.py                # LLM-as-a-judge quality filter
└── synthesis_memos/
    ├── synthetic_data_best_practices.md
    └── llm_as_judge_survey.md
```

## Status (Interim — Wednesday submission)

| Act | Deliverable | Status |
|-----|-------------|--------|
| I | audit_memo.md | ✅ Complete |
| I | schema.json (3 example tasks) | ✅ Complete |
| I | scoring_evaluator.py | ✅ Complete |
| I | methodology.md (Path A declared) | ✅ Complete |
| II | 250-task dataset (train/dev/held_out) | ✅ Complete |
| II | datasheet.md (all 7 Gebru sections) | ✅ Complete |
| II | contamination_check.json | ✅ Complete |
| II | inter_rater_agreement.md | ✅ Complete |
| II | synthesis_memos (2 of 4 common) | ✅ Complete |
| II | cost_log.md | ✅ Complete |
| III–V | Training data prep, training run, ablations, publication | 🔜 Days 4–7 |

## Quick Start (Reproduce Headline Score)

```bash
# 1. Clone and install
git clone <repo-url>
cd tenacious-bench
pip install -r requirements.txt

# 2. Score an agent output against the dev partition
python scoring_evaluator.py \
  --partition dev \
  --agent_outputs path/to/your_outputs.jsonl \
  --output results.json

# 3. Regenerate dataset from scratch (seed=42)
python generation_scripts/generate_dataset.py
```

**Requirements:** Python 3.11+, `nltk`, `scikit-learn`, `numpy`

```
pip install nltk scikit-learn numpy
```

## Baseline (Week 10 Agent on Dev Partition)

| Category | Pass Rate | Notes |
|----------|-----------|-------|
| ICP Misclassification | 62.4% | Segment waterfall ordering bug |
| Bench Over-Commitment | 28.0% | No bench API — all segment=3 emails fail |
| Tone Drift | 54.2% | LLM tone-check false-pass rate 17–38% |
| Hiring-Signal Over-Claiming | 51.7% | Stale job post detection missing |
| Multi-Thread Leakage | 37.5% | In-memory _LEADS dict race condition |
| **Overall dev** | **49.1%** | Baseline for Week 11 training lift |

τ²-Bench retail score (Week 10): **72.7%** (150 traces, retail domain only — not comparable to Tenacious-Bench).

## Training Path

**Path A — SFT a generation component.** Backbone: Qwen 3.5 2B with LoRA (rank=16). Target component: brief-to-email composer. See [methodology.md](methodology.md) for full justification.

## What's Next (Days 4–7)

1. Convert training partition to chat-template SFT format (1,000–3,000 pairs after quality filter).
2. Run LoRA training on Colab T4 via Unsloth (~60 min estimated).
3. Ablate: Delta A (trained vs. Week 10 baseline), Delta B (trained vs. prompt-engineered).
4. Publish dataset to HuggingFace Hub under `mikias-dagem/tenacious-bench-v0.1`.
5. Publish LoRA adapter with model card.
6. Write technical blog post (1,200–2,000 words).
7. File GitHub issue on τ²-Bench repo with gap finding.

## Citation

```bibtex
@dataset{dagem2026tenacious,
  title        = {Tenacious-Bench v0.1: A Sales Agent Evaluation Dataset for B2B Outreach Failure Modes},
  author       = {Mikias Dagem},
  year         = {2026},
  month        = {April},
  institution  = {10 Academy / TRP1},
   
  note         = {250 tasks across 10 failure categories derived from the Tenacious Conversion Engine probe library}
}
```
