# Tenacious-Bench v0.1

**Author:** Mikias Dagem | **Email:** mikias@10academy.org  
**Created:** 2026-04-29 | **Version:** 0.1 (Interim — Acts I & II)  
**License:** CC-BY-4.0

## Overview

Tenacious-Bench is a Tenacious-specific evaluation dataset for the Conversion Engine agent built in Week 10. It measures failure modes that τ²-Bench retail cannot grade: prospect segment misclassification, bench over-commitment, tone drift against the Tenacious style guide, hiring-signal over-claiming, multi-thread data leakage, scheduling timezone errors, and eight other categories derived from 36 documented probes.

**250 tasks** across 10 failure categories. Three partitions: training (50%), public dev (30%), sealed held-out (20%).

## Repository Structure

```
tenacious-bench/
├── README.md                              # Project overview, setup, quick start
├── INDEX.md                               # Complete file index and navigation
│
├── CORE DELIVERABLES (Acts I & II)
├── audit_memo.md                          # Gap analysis: 7 gaps τ²-Bench cannot grade
├── probe_library.md                       # 36 probes across 10 failure categories
├── failure_taxonomy.md                    # 10 categories ranked by ACV risk
├── schema.json                            # Task schema + 3 annotated examples
├── scoring_evaluator.py                   # Deterministic scorer (zero human-in-loop)
├── methodology.md                         # Path A declaration + justification + partitioning
├── methodology_rationale.md               # Path-specific papers + Week 10 trace citations
├── datasheet.md                           # Gebru + Pushkarna documentation (7 sections)
├── model_card.md                          # LoRA adapter card (backbone, hyperparams, eval)
├── inter_rater_agreement.md               # 30-task self-agreement matrix (90% overall)
├── cost_log.md                            # Cost transparency (full week)
├── contamination_check.json               # Validation results (all 3 checks pass)
├── evidence_graph.json                    # Every numeric claim mapped to its source
├── blog_post.md                           # Technical blog post (1,500 words)
│
├── DATASET PARTITIONS
├── tenacious_bench_v0.1/
│   ├── train/tasks.jsonl                  # 125 tasks (50%) — SFT training data
│   ├── dev/tasks.jsonl                    # 71 tasks (28.4%) — public dev partition
│   └── held_out/tasks.jsonl               # 54 tasks (21.6%) — sealed [gitignored]
│
├── TRAINING (Acts III & IV)
├── training_data/
│   ├── prepare_training_data.py           # Converts train partition → SFT chat-template pairs
│   └── sft_pairs.jsonl                    # 1,247 quality-filtered SFT pairs (seed=42)
├── training/
│   ├── train.py                           # Unsloth LoRA training script (run on Colab T4)
│   └── training_run_SIMULATED_by_claude.log  # ⚠️ Replace with real Colab output
├── ablations/
│   ├── ablation_results_SIMULATED_by_claude.json  # ⚠️ Replace after scoring run
│   └── held_out_traces_SIMULATED_by_claude.jsonl  # ⚠️ Replace after scoring run
│
├── GENERATION & VALIDATION
├── generation_scripts/
│   ├── generate_dataset.py                # Reproducible generation (seed=42)
│   ├── contamination_check.py             # N-gram + embedding + time-shift checks
│   └── judge_filter.py                    # LLM-as-judge quality filter (3 dimensions)
│
├── SYNTHESIS MEMOS (4 of 4 complete)
├── synthesis_memos/
│   ├── synthetic_data_best_practices.md   # Liu et al. COLM 2024
│   ├── llm_as_judge_survey.md             # Gu et al. 2024–2025
│   ├── datasheets_and_data_cards.md       # Gebru 2021 + Pushkarna FAccT 2022
│   └── contamination_survey.md            # Chen et al. EMNLP 2025
│
├── CONFIGURATION
├── requirements.txt                       # Python dependencies
├── .gitignore                             # Excludes held_out partition, venv, ablation simulated files
├── pyproject.toml                         # Project metadata
└── .python-version                        # Python 3.11+ requirement
```

### Directory Descriptions

| Directory | Purpose |
|-----------|---------|
| **Root** | Core deliverables, dataset, configuration |
| **tenacious_bench_v0.1/** | 250-task dataset (train/dev/held_out partitions) |
| **generation_scripts/** | Reproducible generation, contamination checks, judge filter |
| **synthesis_memos/** | Critical engagement with common reading papers |

## Status (Final Submission)

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
| II | synthesis_memos (4 of 4 common) | ✅ Complete |
| II | cost_log.md | ✅ Complete |
| III | training_data/sft_pairs.jsonl (1,247 pairs) | ✅ Complete |
| III | methodology_rationale.md | ✅ Complete |
| IV | training/train.py (Unsloth LoRA script) | ✅ Complete |
| IV | training/training_run_seed42.log (real Colab run — 441 steps, loss 0.2883, Qwen3 4B rank=16) | ✅ Complete |
| IV | training/trainer_state.json (real) | ✅ Complete |
| IV | training/sft_loss_curve.png (real) | ✅ Complete |
| IV | ablations/ablation_results (re-run needed with correct held_out file) | ⚠️ Scoring broken — re-run on Kaggle |
| IV | model_card.md | ✅ Complete (updated with real training numbers) |
| V | blog_post.md | ✅ Complete |
| V | evidence_graph.json | ✅ Complete (7 simulated ablation claims; training claims now real) |
| V | HuggingFace dataset URL | ✅ [mike-D83/tenacious-bench-v0.1](https://huggingface.co/datasets/mike-D83/tenacious-bench-v0.1) |
| V | HuggingFace model URL | ✅ [mike-D83/tenacious-bench-sft-adapter-v0.1](https://huggingface.co/mike-D83/tenacious-bench-sft-adapter-v0.1) |
| V | Blog post (Medium) | ✅ [medium.com/@mikiasdagem/when-your-benchmark-lies...](https://medium.com/@mikiasdagem/when-your-benchmark-lies-building-a-sales-domain-evaluation-dataset-from-36-failure-probes-5bfb5eb2feb8) |
| V | Community engagement (τ²-Bench cross-link) | ✅ [github.com/yifanmai/tau2/issues/147](https://github.com/yifanmai/tau2/issues/147) |

## Setup Instructions

### Environment Requirements

- **Python:** 3.11 or higher
- **Key Dependencies:** 
  - `numpy>=1.24.0` — numerical computing
  - `pandas>=2.0.0` — data manipulation
  - `nltk>=3.8.1` — NLP utilities
  - `scikit-learn>=1.3.0` — ML utilities
  - `sentence-transformers>=2.2.0` — embedding similarity checks
  - `openai>=1.0.0`, `anthropic>=0.7.0` — LLM APIs (for generation pipeline)
  - `jsonlines>=4.0.0` — JSONL parsing

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Miked1991/tenacious-bench.git
cd tenacious-bench

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import nltk, sklearn, numpy; print('✅ All dependencies installed')"
```

### Quick Start: Score a Sample Task

```bash
# Score the 3 example tasks from schema.json
python scoring_evaluator.py --demo

# Score the full dev partition
python scoring_evaluator.py --partition dev --output dev_results.json

# Score a specific task
python scoring_evaluator.py --task TB-0001
```

### Regenerate Dataset from Scratch

```bash
# Reproducible generation (seed=42)
python generation_scripts/generate_dataset.py

# Output: 125 train, 71 dev, 54 held_out tasks
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

**Path A — SFT a generation component.** Backbone: Qwen3 4B (`unsloth/Qwen3-4B-bnb-4bit`) with LoRA (rank=16). Target component: brief-to-email composer. See [methodology.md](methodology.md) for full justification.

## Immediate Next Steps (v0.1 Cleanup)

1. **Measure Delta B** — run prompt-engineered baseline: `python ablations/delta_b_eval.py --trained_results ablation_results.json` on Colab T4. Until this runs, the claim that SFT outperforms prompting is unconfirmed.
2. **Re-train with probe-level split** — `python training_data/generate_full_training_data.py` now outputs `sft_train.jsonl` / `sft_eval.jsonl` with zero probe_id overlap. Re-run `python training/train.py` to get a valid eval loss.
3. **Apply architectural patches** — copy `_classify_segment` fix and `threading.Lock` LEADS store from `agent_fixes/conversion_engine_patches.py` into the Conversion Engine repo. These are 2-line + 5-line changes; ICP misclassification (currently +1.7pp) should climb to ~62% after the reorder.

## v0.2 Roadmap

The following four failure modes are documented but not yet captured in the evaluation dataset. Each entry includes the specific implementation needed.

### 1. Multi-turn tone drift (Probe P16)

**Gap:** v0.1 only evaluates cold outreach (single-turn). Probe P16 documents 38% tone escalation by reply turn 3 — the agent introduces urgency language ("I wanted to follow up again…") not present in the cold email. This cannot be caught by a single-turn rubric.

**v0.2 implementation:**

- Add a `multi_turn` task type to `schema.json` with fields: `turn_history` (list of prior messages), `current_turn` (new assistant response to score).
- Extend `scoring_evaluator.py` with a `turn_number` dimension: flag escalation phrases appearing in turns 2+ that were absent in turn 1.
- Target: 30 multi-turn tasks (10 per escalation pattern: urgency injection, tone downgrade, over-commitment creep).

### 2. Real-time bench state integration (Probes P11–P13)

**Gap:** The current `bench_commitment_accuracy` rubric evaluates bench commitment as a static flag. A real evaluation must check whether the committed headcount was actually available at the time of the outreach — the bench state changes between runs.

**v0.2 implementation:**

- Add a `bench_state_at_send` field to each task's `input` capturing the bench snapshot at the moment the email was generated.
- Extend `scoring_evaluator.py` to cross-check any implicit headcount reference in the email against `bench_state_at_send` (not just the static `bench_available` field in the task).
- Target: expand the bench_over_commitment category from 6 to 15 held-out tasks with varied bench depletion scenarios.

### 3. Competitor gap brief staleness (Probes P35–P36)

**Gap:** The rubric checks whether a competitor gap is referenced, not whether the gap data is recent enough to be credible. A gap brief from 14 months ago (e.g., "Competitor X raised Series B") is no longer actionable.

**v0.2 implementation:**

- Add a `gap_brief_date` field to tasks using competitor gap signals.
- Add a `gap_recency_ok` rubric dimension: fail if the gap_brief_date is more than 180 days before the email send date.
- Expand gap_over_claiming from 4 held-out tasks (currently has the widest CI in the dataset) to at least 8 tasks — this category's n=4 makes its ±40pp CI directional-only.

### 4. Dynamic contamination defense

**Gap:** The held-out partition is static. After the leaderboard publishes, dev tasks enter the training corpora of public models. A static held-out loses its integrity.

**v0.2 implementation:**

- Implement template mutation in `generation_scripts/generate_dataset.py`: randomise surface-form values (company names, funding amounts, dates) at evaluation time while keeping the underlying rubric fixed. Follow Chen et al. (EMNLP 2025) §4.3.
- Add a `mutation_seed` parameter so evaluations are reproducible within a leaderboard window but change across versions.
- Each v0.2 held-out task should carry a `canonical_form` (fixed rubric) and a `surface_form` (mutated at eval time) — the scorer reads from `canonical_form`, the model sees `surface_form`.

### 5. Minimum category size enforcement

**Gap:** 5 of 10 held-out categories have n < 6, producing ±30–40pp bootstrap CIs. These are directional-only estimates.

**v0.2 target:** Enforce a minimum of 8 tasks per category in held-out. This gives a 95% CI width of approximately ±25pp at the category level — still wide, but reliable enough to distinguish 40pp+ lifts from noise. Update `generate_dataset.py` with a `--min_held_out_per_cat 8` guard that rejects the partition if any category falls below the threshold.

## Major Artifacts

### Documentation
- **[audit_memo.md](audit_memo.md)** — 600-word gap analysis with 8+ probe IDs and 5+ trace IDs
- **[datasheet.md](datasheet.md)** — Gebru + Pushkarna documentation (all 7 sections)
- **[methodology.md](methodology.md)** — Path A declaration with Week 10 evidence and contamination results
- **[probe_library.md](probe_library.md)** — 36 probes across 10 categories with trigger rates and costs
- **[failure_taxonomy.md](failure_taxonomy.md)** — 10 categories ranked by business-cost impact

### Evaluation & Validation
- **[schema.json](schema.json)** — Task schema + 3 annotated example tasks
- **[scoring_evaluator.py](scoring_evaluator.py)** — Deterministic scorer with rubric decomposition
- **[inter_rater_agreement.md](inter_rater_agreement.md)** — 30-task self-agreement matrix (90% overall)
- **[contamination_check.json](contamination_check.json)** — N-gram, embedding, time-shift validation

### Synthesis & Analysis
- **[synthesis_memos/](synthesis_memos/)** — Critical engagement with common reading papers
- **[SCORING_REPORT.md](SCORING_REPORT.md)** — Comprehensive scoring analysis across all partitions
- **[TENACIOUS_BENCH_V0.1_REPORT.pdf](TENACIOUS_BENCH_V0.1_REPORT.pdf)** — Executive PDF report

## Citation

```bibtex
@dataset{dagem2026tenacious,
  title        = {Tenacious-Bench v0.1: A Sales Agent Evaluation Dataset for B2B Outreach Failure Modes},
  author       = {Mikias Dagem},
  year         = {2026},
  month        = {April},
  institution  = {10 Academy / TRP1},
  url          = {https://github.com/Miked1991/tenacious-bench},
  note         = {250 tasks across 10 failure categories derived from the Tenacious Conversion Engine probe library. CC-BY-4.0 license.}
}
```
