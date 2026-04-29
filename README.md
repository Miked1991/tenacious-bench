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
├── datasheet.md                           # Gebru + Pushkarna documentation (7 sections)
├── inter_rater_agreement.md               # 30-task self-agreement matrix (90% overall)
├── cost_log.md                            # Cost transparency ($47.32 total)
├── contamination_check.json               # Validation results (all 3 checks pass)
│
├── DATASET PARTITIONS
├── tenacious_bench_v0.1/
│   ├── train/tasks.jsonl                  # 125 tasks (50%) — SFT training data
│   ├── dev/tasks.jsonl                    # 71 tasks (28.4%) — public dev partition
│   └── held_out/tasks.jsonl               # 54 tasks (21.6%) — sealed evaluation set
│
├── GENERATION & VALIDATION
├── generation_scripts/
│   ├── generate_dataset.py                # Reproducible generation (seed=42)
│   ├── contamination_check.py             # N-gram + embedding + time-shift checks
│   └── judge_filter.py                    # LLM-as-judge quality filter (3 dimensions)
├── generate_pdf_report.py                 # PDF report generation script
│
├── SYNTHESIS & DOCUMENTATION
├── synthesis_memos/
│   ├── synthetic_data_best_practices.md   # Best practices for synthetic task generation
│   └── llm_as_judge_survey.md             # LLM-as-judge approaches & calibration
├── SCORING_REPORT.md                      # Comprehensive scoring analysis
├── TENACIOUS_BENCH_V0.1_REPORT.pdf        # Executive PDF report
│
├── CONFIGURATION
├── requirements.txt                       # Python dependencies
├── .gitignore                             # Excludes held_out partition
├── CHANGELOG.md                           # Version history
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

## What's Next (Days 4–7)

1. Convert training partition to chat-template SFT format (1,000–3,000 pairs after quality filter).
2. Run LoRA training on Colab T4 via Unsloth (~60 min estimated).
3. Ablate: Delta A (trained vs. Week 10 baseline), Delta B (trained vs. prompt-engineered).
4. Publish dataset to HuggingFace Hub under `mikias-dagem/tenacious-bench-v0.1`.
5. Publish LoRA adapter with model card.
6. Write technical blog post (1,200–2,000 words).
7. File GitHub issue on τ²-Bench repo with gap finding.

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
