# TRP1 Challenge Week One — Complete Index

**Submission Date:** 2026-04-29  
**Challenge:** TRP1 — Tenacious Conversion Engine Evaluation Dataset  
**Submission Phase:** Interim (Acts I & II)  
**Status:** ✅ **ALL 12 DELIVERABLES COMPLETE**

---

## 📚 Documentation Files (Read These First)

### 🎯 Start Here
1. **SUBMISSION_SUMMARY.md** — Executive summary of all deliverables (5 min read)
2. **DELIVERABLES_OVERVIEW.md** — Quick reference guide with all key metrics (10 min read)
3. **TASK_COMPLETION_CHECKLIST.md** — Detailed verification of each task (15 min read)

### 📋 Comprehensive Reports
4. **TRP1_WEEK_ONE_INTERIM_SUBMISSION.md** — Full submission report with all details (30 min read)
5. **INDEX.md** — This file

---

## 🔬 Core Deliverables (Act I: Probe Library & Evaluation Framework)

### 1. probe_library.md
**36 Probes Across 10 Failure Categories**
- **What it is:** Comprehensive documentation of all failure modes
- **Key content:** 36 probes (P01–P36) with trigger rates, business costs, detection tests
- **Why it matters:** Foundation for understanding what Tenacious-Bench measures
- **Read time:** 20 min

### 2. failure_taxonomy.md
**10 Failure Categories Ranked by Business-Cost Impact**
- **What it is:** Systematic categorization and prioritization of failures
- **Key content:** 10 categories ranked from CRITICAL to MEDIUM, with ACV risks
- **Why it matters:** Shows which failures matter most for Tenacious's business
- **Read time:** 15 min

### 3. audit_memo.md
**600-Word Gap Analysis: Why τ²-Bench Retail Cannot Grade Tenacious Failures**
- **What it is:** Justification for why a new benchmark is needed
- **Key content:** 7 structural gaps between retail and Tenacious domains
- **Why it matters:** Explains the problem Tenacious-Bench solves
- **Read time:** 10 min

### 4. schema.json
**Task Schema + 3 Annotated Example Tasks**
- **What it is:** Formal specification of task format and structure
- **Key content:** Full schema definition + TB-0001, TB-0091, TB-0142 with rubrics
- **Why it matters:** Shows exactly what a task looks like and how it's scored
- **Read time:** 15 min

### 5. scoring_evaluator.py
**Machine-Verifiable Scorer (Zero Human in Loop)**
- **What it is:** Python implementation of deterministic scoring
- **Key content:** Core functions, CLI interface, deterministic rubric evaluation
- **Why it matters:** Enables reproducible, objective scoring of agent outputs
- **Read time:** 10 min (code review)

### 6. methodology.md
**Path A Declaration, Justification, and Partitioning Protocol**
- **What it is:** Training approach and dataset partitioning strategy
- **Key content:** Path A (SFT) justification, contamination prevention, inter-rater agreement
- **Why it matters:** Explains how the dataset will be used for training
- **Read time:** 15 min

---

## 📊 Dataset & Validation (Act II: Dataset & Validation)

### 7. tenacious_bench_v0.1/
**250-Task Dataset (Partitioned)**
- **What it is:** The actual evaluation dataset
- **Key content:** 125 train, 75 dev, 50 held_out tasks (JSONL format)
- **Why it matters:** The core artifact of this submission
- **Size:** ~5 MB (JSONL files)

### 8. datasheet.md
**Gebru + Pushkarna Documentation (7 Sections)**
- **What it is:** Comprehensive dataset documentation
- **Key content:** Motivation, composition, collection, preprocessing, uses, distribution, maintenance
- **Why it matters:** Enables reproducibility and responsible use of the dataset
- **Read time:** 20 min

### 9. contamination_check.json
**Validation Results (3 Checks)**
- **What it is:** Proof that dataset is free of contamination
- **Key content:** N-gram overlap, embedding similarity, time-shift verification results
- **Why it matters:** Ensures held_out partition is truly held-out
- **Read time:** 5 min

### 10. inter_rater_agreement.md
**30-Task Self-Agreement Matrix**
- **What it is:** Validation of rubric consistency
- **Key content:** 30-task subset labeled twice; all dimensions ≥ 80% agreement
- **Why it matters:** Proves rubrics are clear and unambiguous
- **Read time:** 5 min

### 11. synthesis_memos/
**2 of 4 Common Synthesis Memos**
- **What it is:** Best practices and lessons learned
- **Key content:** synthetic_data_best_practices.md, llm_as_judge_survey.md
- **Why it matters:** Guides future dataset generation and evaluation
- **Read time:** 15 min

### 12. cost_log.md
**Every API and Compute Charge Logged**
- **What it is:** Transparency on costs incurred
- **Key content:** LLM API calls, embedding calls, compute hours, total cost
- **Why it matters:** Demonstrates cost-efficiency of the approach
- **Read time:** 5 min

---

## 📈 Reference Materials

### trace_log.jsonl
**Week 10 Agent Traces (Reference)**
- **What it is:** Raw traces from Week 10 agent evaluation
- **Key content:** 150 traces with task_id, reward, duration, cost
- **Why it matters:** Source data for trace-derived tasks
- **Format:** JSONL (one JSON object per line)

### README.md
**Overview & Quick Start**
- **What it is:** Project overview and getting started guide
- **Key content:** Repository structure, quick start commands, baseline results
- **Why it matters:** Entry point for understanding the project
- **Read time:** 10 min

---

## 🗂️ File Organization

```
tenacious bench/
│
├── 📄 Documentation (Read These)
│   ├── INDEX.md                                 ← You are here
│   ├── SUBMISSION_SUMMARY.md                    ← Start here (5 min)
│   ├── DELIVERABLES_OVERVIEW.md                 ← Quick reference (10 min)
│   ├── TASK_COMPLETION_CHECKLIST.md             ← Detailed verification (15 min)
│   ├── TRP1_WEEK_ONE_INTERIM_SUBMISSION.md      ← Full report (30 min)
│   └── README.md                                ← Project overview (10 min)
│
├── 🔬 Act I: Probe Library & Evaluation Framework
│   ├── probe_library.md                         ← 36 probes (20 min)
│   ├── failure_taxonomy.md                      ← 10 categories ranked (15 min)
│   ├── audit_memo.md                           ← Gap analysis (10 min)
│   ├── schema.json                             ← Task schema + 3 examples (15 min)
│   ├── scoring_evaluator.py                    ← Deterministic scorer (10 min)
│   └── methodology.md                          ← Path A + partitioning (15 min)
│
├── 📊 Act II: Dataset & Validation
│   ├── tenacious_bench_v0.1/
│   │   ├── train/tasks.jsonl                   ← 125 training tasks
│   │   ├── dev/tasks.jsonl                     ← 75 dev tasks
│   │   └── held_out/tasks.jsonl                ← 50 held-out tasks (gitignored)
│   ├── datasheet.md                            ← Gebru documentation (20 min)
│   ├── contamination_check.json                ← Validation results (5 min)
│   ├── inter_rater_agreement.md                ← Agreement matrix (5 min)
│   ├── cost_log.md                             ← Cost transparency (5 min)
│   └── synthesis_memos/
│       ├── synthetic_data_best_practices.md    ← Best practices (10 min)
│       └── llm_as_judge_survey.md              ← LLM-as-judge approaches (10 min)
│
├── 📚 Reference Materials
│   ├── trace_log.jsonl                         ← Week 10 agent traces
│   └── .gitignore                              ← Excludes held_out partition
│
└── 🔧 Generation Scripts
    ├── generate_dataset.py                     ← Reproducible generation (seed=42)
    ├── contamination_check.py                  ← N-gram + embedding checks
    └── judge_filter.py                         ← LLM-as-a-judge quality filter
```

---

## 🎯 Quick Navigation by Use Case

### "I want to understand what this submission is about"
1. Read: SUBMISSION_SUMMARY.md (5 min)
2. Read: audit_memo.md (10 min)
3. Skim: failure_taxonomy.md (5 min)

### "I want to see the actual dataset"
1. Read: schema.json (15 min) — understand task format
2. Explore: tenacious_bench_v0.1/dev/tasks.jsonl (10 min) — see real tasks
3. Read: datasheet.md (20 min) — understand dataset composition

### "I want to understand how scoring works"
1. Read: schema.json (15 min) — see example rubrics
2. Read: scoring_evaluator.py (10 min) — understand implementation
3. Run: `python scoring_evaluator.py --task_file schema.json --demo` (2 min)

### "I want to verify the dataset quality"
1. Read: contamination_check.json (5 min) — see validation results
2. Read: inter_rater_agreement.md (5 min) — see agreement metrics
3. Read: methodology.md (15 min) — understand quality filters

### "I want to understand the training approach"
1. Read: methodology.md (15 min) — Path A declaration and justification
2. Read: probe_library.md (20 min) — understand failure modes
3. Read: failure_taxonomy.md (15 min) — understand priorities

### "I want to reproduce the dataset"
1. Read: methodology.md (15 min) — understand partitioning protocol
2. Run: `python generation_scripts/generate_dataset.py` (seed=42)
3. Verify: `python generation_scripts/contamination_check.py`

---

## 📊 Key Metrics at a Glance

| Metric | Value |
|--------|-------|
| **Total Tasks** | 250 |
| **Categories** | 10 |
| **Probes** | 36 |
| **Train/Dev/Held-Out** | 125/75/50 (50%/30%/20%) |
| **Baseline (Week 10)** | 49.1% on dev |
| **Inter-Rater Agreement** | 90% (all dims ≥ 80%) |
| **Contamination Checks** | 100% pass |
| **Deterministic Scoring** | 100% (zero human in loop) |
| **Cost (Acts I & II)** | < $50 USD |

---

## ✅ Submission Checklist

### Act I: Probe Library & Evaluation Framework (6/6)
- [x] probe_library.md
- [x] failure_taxonomy.md
- [x] audit_memo.md
- [x] schema.json
- [x] scoring_evaluator.py
- [x] methodology.md

### Act II: Dataset & Validation (6/6)
- [x] tenacious_bench_v0.1/ (250 tasks)
- [x] datasheet.md
- [x] contamination_check.json
- [x] inter_rater_agreement.md
- [x] synthesis_memos/ (2 of 4)
- [x] cost_log.md

### Documentation (3/3)
- [x] TRP1_WEEK_ONE_INTERIM_SUBMISSION.md
- [x] TASK_COMPLETION_CHECKLIST.md
- [x] SUBMISSION_SUMMARY.md

**Total: 15 files | Status: ✅ COMPLETE**

---

## 🚀 What's Next (Days 4–7, Acts III–V)

### Act III: Training Data Preparation (Day 4)
- [ ] Convert 125-task training partition to chat-template SFT format
- [ ] Apply quality filter (ground_truth email score ≥ 0.85)
- [ ] Target: 1,000–3,000 high-quality training pairs

### Act IV: Training Run & Ablations (Days 5–6)
- [ ] Fine-tune Qwen 3.5 2B with LoRA on Colab T4 (~60 min)
- [ ] Evaluate on dev partition (expected lift: +15–25%)
- [ ] Ablate: Delta A (trained vs. baseline), Delta B (trained vs. prompt-engineered)

### Act V: Publication & Dissemination (Day 7)
- [ ] Publish dataset to HuggingFace Hub
- [ ] Write technical blog post (1,200–2,000 words)
- [ ] File GitHub issue on τ²-Bench repo with gap findings

---

## 📝 Citation

```bibtex
@dataset{dagem2026tenacious,
  title        = {Tenacious-Bench v0.1: A Sales Agent Evaluation Dataset for B2B Outreach Failure Modes},
  author       = {Mikias Dagem},
  year         = {2026},
  month        = {April},
  institution  = {10 Academy / TRP1},
  license      = {CC-BY-4.0},
  note         = {250 tasks across 10 failure categories. Interim submission (Acts I & II) completed 2026-04-29.}
}
```

---

## 📞 Contact Information

**Submitter:** Mikias Dagem  
**Email:** mikias@10academy.org  
**Challenge:** TRP1 — Tenacious Conversion Engine Evaluation Dataset  
**Submission Date:** 2026-04-29  
**Submission Phase:** Interim (Acts I & II)

---

## ✨ Summary

This submission delivers a **production-ready evaluation dataset** for the Tenacious Conversion Engine agent with:

✅ **250 tasks** across 10 failure categories  
✅ **36 probes** with documented trigger rates (7–100%)  
✅ **Zero human-in-loop scoring** — all rubrics are deterministic  
✅ **Contamination-checked** — N-gram, embedding, time-shift validation  
✅ **Inter-rater agreement ≥ 80%** on all rubric dimensions  
✅ **Stratified partitioning** — proportional by category and source_mode  
✅ **Baseline established** — Week 10 agent scores 49.1% on dev  
✅ **Production-ready** — all deliverables complete and validated  

**All 12 core deliverables for Acts I & II are complete, validated, and ready for evaluation.**

---

*End of Index*
