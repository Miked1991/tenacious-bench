---
title: "When Your Benchmark Lies: Building a Sales-Domain Evaluation Dataset from 36 Failure Probes"
thumbnail: https://huggingface.co/datasets/mike-D83/tenacious-bench-v0.1/resolve/main/thumbnail.png
authors:
  - user: mike-D83
tags:
  - dataset
  - evaluation
  - sft
  - lora
  - b2b
  - sales-agent
  - benchmarking
---

# When Your Benchmark Lies: Building a Sales-Domain Evaluation Dataset from 36 Failure Probes

**Dataset:** [mike-D83/tenacious-bench-v0.1](https://huggingface.co/datasets/mike-D83/tenacious-bench-v0.1)  
**Adapter:** [mike-D83/tenacious-bench-sft-adapter-v0.1](https://huggingface.co/mike-D83/tenacious-bench-sft-adapter-v0.1)  
**Code:** [Miked1991/tenacious-bench](https://github.com/Miked1991/tenacious-bench)

---

## The Problem: A 72.7% Score That Means Nothing

In Week 10 of TRP1 I built the Tenacious Conversion Engine — an agent that finds B2B engineering prospects, grounds outreach in public signals (Crunchbase, hiring pages, PDL, layoffs.fyi), classifies them by segment, and composes a cold email that references the specific trigger that made them a prospect today.

My agent scored **72.7% on τ²-Bench retail** — a public benchmark for shopping-task agents. Not bad. But that number tells me exactly nothing about whether my agent writes emails that comply with Tenacious's 18-phrase banned list. It tells me nothing about whether it commits to headcount numbers the bench cannot deliver. It tells me nothing about whether it books EU prospects at 1am local time.

τ²-Bench retail evaluates whether an agent can add items to a cart, apply discount codes, and track shipments. Tenacious's failures are: over-claiming a stale hiring signal, writing "leverage our AI-powered platform" in a cold email, promising 10 ML engineers in two weeks when the bench has six. These are structurally incompatible evaluation targets.

The benchmark was lying to me by omission.

---

## The Audit: Finding the Gap

I documented the lie systematically. Starting from the Week 10 trace log — 150 agent runs with final-turn rewards — I built a **probe library**: 36 specific failure probes, each with a trigger input, observed failure, trigger rate, and business cost.

The findings were stark. Seven categories of failure that τ²-Bench cannot observe:

1. **Signal-confidence-aware language generation.** The style guide requires interrogative phrasing when Crunchbase confidence is below 0.7, assertive phrasing only above. Probe P06 shows the agent over-claiming "aggressive hiring" from a single stale job post in 34% of runs.

2. **Bench commitment accuracy.** Probe P11 shows 100% of segment=3 emails containing unqualified "scale rapidly" language when the bench cannot deliver. The agent has no learned constraint against headcount promises.

3. **Tone and banned-phrase compliance.** The Tenacious style guide bans 18 phrases. Probe P14 shows the LLM tone-check passes 17% of emails containing banned phrases. Probe P15 shows 24% of cold emails exceeding the 120-word limit despite passing tone-check.

4. **Timezone-aware scheduling.** Probe P27 shows 18% of EU prospects booked at local midnight.

The Week 10 agent's actual score on these failure modes: **49.1% on a 250-task Tenacious-specific evaluation set** — barely above random. The 72.7% retail score was measuring a different agent on a different task.

---

## The Dataset: 250 Tasks, 10 Categories, Zero Human Graders

A rubric that says "the email should sound professional" is not a benchmark. A rubric that says "the email contains zero of these 18 banned phrases AND references the exact funding amount from the signal AND word count ≤ 120" is.

[Tenacious-Bench v0.1](https://huggingface.co/datasets/mike-D83/tenacious-bench-v0.1) is 250 tasks across 10 failure categories, built from 4 authoring modes:

| Mode | Share | Description |
|------|-------|-------------|
| Programmatic | 40% | Parameter sweeps over probe specs (funding stage × bench state × signal confidence) |
| Trace-derived | 30% | Real Week 10 agent outputs restructured into (input, failing output, rubric) triples |
| Multi-LLM synthesis | 20% | Claude authors, Qwen judges — and vice versa — to prevent preference leakage |
| Hand-authored | 10% | Adversarial edge cases the synthesis pipeline misses |

**Three partitions:** 125 train (50%) / 71 dev (28.4%) / 54 held-out (21.6%, sealed).

**Quality controls:**
- LLM-as-judge filter: ≥ 4/5 on input coherence, ground-truth verifiability, rubric clarity
- N-gram contamination: 0 overlaps (8-gram) across 6,750 held_out–train pairs
- Embedding similarity: max cosine 0.82 (threshold 0.85)
- Inter-rater agreement: 90% overall across 30-task re-labeling protocol

---

## The Training Experiment: Path A SFT

Week 10's failures concentrated in Tone Drift (54.2% pass rate) and Bench Over-Commitment (28.0%). Both are generation-quality failures — the model produces output that violates explicit style constraints. This is exactly what SFT addresses.

I trained a LoRA adapter (rank=8, alpha=16) on **Qwen 3.5 2B** using [Unsloth](https://github.com/unslothai/unsloth) on Colab T4 (free tier):

```
Model  : unsloth/Qwen3-4B-bnb-4bit
LoRA   : r=8, alpha=16, dropout=0.05
LR     : 1e-4 (cosine schedule, warmup 10%)
Batch  : 2 × 4 grad accum = effective batch 8
Epochs : 3
Steps  : 441
Runtime: 5,871s (~98 min) on T4

Final train loss : 0.2883
Best eval loss   : 0.0213  ← checkpoint-441
```

Training data: **1,247 SFT pairs** in chat-template format, quality-filtered from 125 seed tasks × 12 Magpie-style variants. Without rubric filtering, ~40% of Magpie-generated pairs violated the style guide in the *ground truth* — teaching the model the wrong behavior. Fix: every pair must score ≥ 0.85 on `scoring_evaluator.py` before entering training.

The adapter and full training log are on the Hub: [mike-D83/tenacious-bench-sft-adapter-v0.1](https://huggingface.co/mike-D83/tenacious-bench-sft-adapter-v0.1)

---

## What SFT Fixes — and What It Doesn't

**What the adapter targets:**
- Tone Drift: zero banned phrases, correct register for CTO audience
- Bench Over-Commitment: no headcount promises without explicit scoping language
- Signal grounding: email must reference the specific signal trigger (funding amount, role count)
- Word count: ≤ 120 words on cold outreach

**What SFT cannot fix:**
Multi-Thread Leakage — this category tests async race conditions in the agent's `_LEADS` dict under concurrent load. SFT of the email composer has no effect on architecture-level bugs. I report this explicitly: an honest benchmark tells you what *didn't* improve, not just what did.

---

## Honest Evaluation Design

Three comparisons matter:

- **Delta A:** Trained LoRA vs. Week 10 baseline on held-out (the main result)
- **Delta B:** Trained LoRA vs. prompt-engineered control — tests whether training beats careful prompting with the full style guide in the system prompt
- **Delta C:** Effect on τ²-Bench retail — should be near-zero; improvement must be domain-specific

Held-out ablation is running. Results will be updated in the [evidence graph](https://github.com/Miked1991/tenacious-bench/blob/master/evidence_graph.json) as each claim is verified against its source artifact.

---

## What's Next: v0.2 Targets

Four failure modes Tenacious-Bench v0.1 does not yet capture:

1. **Real-time bench state:** Current rubric evaluates bench_commitment as a static flag. Real evaluation needs dynamic availability checks.
2. **Multi-turn tone maintenance:** Probe P16 shows 38% tone escalation at turn 3. v0.1 only evaluates cold outreach (turn 1).
3. **Gap brief staleness:** Probes P35–P36 test whether stale competitor gaps are time-qualified. The current rubric is incomplete.
4. **Dynamic contamination defense:** After the leaderboard publishes, dev tasks enter public training corpora. v0.2 will implement template mutation (surface-form randomization at eval time) following Chen et al., EMNLP 2025.

---

## Use It

The dataset, adapter, and all evaluation code are public under **CC-BY-4.0**.

```bash
# Load the dataset
from datasets import load_dataset
ds = load_dataset("mike-D83/tenacious-bench-v0.1")

# Score a single task
python scoring_evaluator.py --demo

# Score the full dev partition
python scoring_evaluator.py --partition dev --output dev_results.json
```

If you're building a B2B sales agent and want to evaluate against Tenacious-specific failure modes — or if you want to contribute adversarial tasks for v0.2 — open a PR or file an issue on the [repo](https://github.com/Miked1991/tenacious-bench).

---

*Mikias Dagem is a TRP1 trainee at 10 Academy. This work was completed as part of the TRP1 Week 11 challenge: Building the Sales Evaluation Bench and Aligning the Conversion Engine.*
