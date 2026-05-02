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
| IV | training/training_run_seed42.log (real Colab run — 441 steps, loss 0.2883) | ✅ Complete |
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

**Path A — SFT a generation component.** Backbone: Qwen 3.5 2B with LoRA (rank=16). Target component: brief-to-email composer. See [methodology.md](methodology.md) for full justification.

## To Complete (After Colab Training Run)

1. Run `python training_data/prepare_training_data.py --seed 42 --min_score 0.85` → generates `sft_pairs.jsonl`
2. Run `python training/train.py --push_to_hub` on Colab T4 (~60 min, free)
3. Score trained model on held-out: `python scoring_evaluator.py --partition held_out --agent_outputs <outputs.jsonl>`
4. Replace the 3 `_SIMULATED_by_claude` files with real output
5. Update `evidence_graph.json` simulated claims (EG-018 to EG-027) with real values
6. ~~Publish dataset to HuggingFace Hub~~ — ✅ [mike-D83/tenacious-bench-v0.1](https://huggingface.co/datasets/mike-D83/tenacious-bench-v0.1)
7. ~~Publish LoRA adapter~~ — ✅ [mike-D83/tenacious-bench-sft-adapter-v0.1](https://huggingface.co/mike-D83/tenacious-bench-sft-adapter-v0.1)
8. Publish `blog_post.md` to HuggingFace community blog or personal site
9. File GitHub issue on τ²-Bench repo linking the dataset

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
