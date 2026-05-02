# Synthesis Memo: Recent Advances in LLM Benchmarks Against Data Contamination

**Author:** Mikias Dagem | **Date:** 2026-05-01  
**Paper:** Chen et al. (EMNLP 2025) *Recent Advances in Large Language Model Benchmarks against Data Contamination: From Static to Dynamic Evaluation*  
**Application:** Contamination-prevention protocol for Tenacious-Bench v0.1 held-out partition

---

## Core Argument of the Paper

Chen et al. survey contamination incidents across 20+ major benchmarks and categorize contamination into four types:

1. **Exact-match contamination:** The held-out example appears verbatim in training data. Classic case: GPT-4's HumanEval performance partially explained by exact-match leakage.

2. **Semantic contamination:** The held-out example does not appear verbatim but a semantically equivalent example does. Cosine similarity above 0.85–0.90 between held-out and training embeddings is the operational threshold the paper identifies.

3. **Temporal contamination:** Benchmarks with static ground truth based on world-state at time T₀ are contaminated when models trained on data past T₀ are evaluated at T₁ > T₀. The model has seen the answer, not because the benchmark was in training data, but because the world-state at T₁ matches the benchmark's ground truth.

4. **Style contamination:** Even when no specific example is leaked, the distribution of the benchmark (answer format, difficulty, domain vocabulary) may be over-represented in training data. Models appear to generalize when they are actually exploiting stylistic cues.

The authors propose a taxonomy of defenses — static (n-gram, embedding, canary tokens), dynamic (template mutation, held-out rotation, live-instance generation), and protocol-based (time-gated release, sealed partitions) — and argue that no single defense is sufficient; defense-in-depth is required.

---

## Application to Tenacious-Bench v0.1

### Three-check contamination protocol

The `contamination_check.json` and `generation_scripts/contamination_check.py` implement the paper's static defense layer:

**Check 1 — N-gram overlap (exact-match defense):**  
8-gram overlap between held-out input fields and train partition. Threshold: 0 overlaps permitted. Result: 0 overlaps across 6,750 held_out-vs-train pairs (54 × 125). This matches the paper's recommendation for strict n-gram filtering on narrow-domain benchmarks where paraphrases are rare.

**Check 2 — Embedding similarity (semantic defense):**  
Cosine similarity between held-out and train task embeddings using `all-MiniLM-L6-v2`. Threshold: < 0.85. Result: maximum similarity 0.82. The 0.85 threshold is taken directly from Chen et al.'s operational recommendation for task-level embedding contamination.

**Check 3 — Time-shift verification (temporal defense):**  
All tasks referencing public signals (funding dates, layoff dates, leadership changes) are anchored to the documented evaluation window (2026-01-01 to 2026-04-25). No generic "DATE" placeholders. Result: all 250 tasks pass. This addresses the temporal contamination type: a model trained on post-window data cannot gain an advantage from knowing the world-state, because all signal dates are within a documented past window.

### What the paper's dynamic defenses would add in v0.2

Chen et al. argue that static defenses are insufficient for long-lived benchmarks because:
- Models trained after the benchmark is published may have ingested the dev partition
- Static n-gram and embedding checks cannot catch style contamination

For v0.2, Tenacious-Bench should add:
- **Template mutation:** Randomize prospect names, company domains, and signal values at evaluation time (the task *structure* remains fixed but the surface form changes per evaluation run)
- **Live-instance generation:** Pull fresh Crunchbase and layoffs.fyi signals at evaluation time and generate new tasks dynamically, rather than evaluating against the static dataset

---

## Where I Disagree with the Paper

### Disagreement 1: The 0.85 embedding threshold is too permissive for narrow-domain benchmarks

Chen et al. recommend cosine similarity < 0.85–0.90 as the threshold for semantic contamination. This range was calibrated on general-domain benchmarks (MMLU, HumanEval, GSM8K) where the embedding space is broad and 0.85 similarity represents a meaningful semantic distance.

For Tenacious-Bench, the task space is narrow: all tasks describe B2B outreach scenarios with similar structural elements (prospect domain, signal type, email requirement). The baseline embedding similarity between *unrelated* tasks in the dataset averages 0.71 — already high by general-domain standards. At 0.85, two tasks could differ only in the company name and funding amount while having near-identical rubric requirements and expected behavior.

**Evidence:** During dataset construction, 3 held-out tasks initially had similarities of 0.83–0.84 (below the 0.85 threshold) with train tasks. Manual inspection revealed these were functionally near-identical (same probe, same parameter values, different company names). They were regenerated. The paper's threshold would have passed them.

**Applied fix:** For narrow-domain benchmarks, I recommend a lower threshold of 0.80 and supplementing with a rubric-overlap check: two tasks are considered contaminated if they share the same probe_id AND the same dominant scoring dimension AND similarity > 0.75. This is implemented in `generation_scripts/contamination_check.py` as an additional check beyond the paper's recommended protocol.

### Disagreement 2: The paper underweights scorer contamination

Chen et al. focus entirely on example-level contamination (held-out tasks leaking into training data). They do not address *scorer contamination*: the case where the scoring model (the LLM-as-judge) has been trained on evaluation rubrics that resemble the benchmark's rubric.

For Tenacious-Bench, the LLM-as-judge (Claude Sonnet 4.6 for spot-checks, Qwen3-Next-80B for bulk filtering) may have been trained on datasets that include similar B2B email evaluation rubrics, creating implicit scorer contamination. The judge has never seen the specific Tenacious style guide, but it has seen "does this email sound professional" rubrics that partially overlap.

**Applied fix:** The model rotation policy (tasks generated by Claude judged by Qwen, and vice versa) reduces preference leakage (per Li et al., 2025) but does not eliminate scorer contamination. The IRA protocol — self-agreement on 30 tasks at 90% overall — provides empirical evidence that the *rubric* is reliable, even if the judge model may have scorer contamination. This is a practical defense that the paper's framework does not address.

---

## Key Design Decision Influenced by This Paper

The decision to **seal the held-out partition by gitignoring it** (rather than publishing it with the dataset and trusting users not to train on it) was directly motivated by Chen et al.'s documentation of how quickly contamination propagates after publication. The paper cites cases where held-out sets were ingested into training data within weeks of public release.

The gitignored held_out/tasks.jsonl is held locally and released only after the leaderboard closes. This is a protocol-based defense from the paper's taxonomy, and it is the strongest single defense for a small benchmark without the resources to implement dynamic evaluation at v0.1.

---

## One-Sentence Summary

Chen et al. provide the right taxonomy and the 0.85 embedding threshold, but their thresholds are calibrated on general-domain benchmarks and underestimate semantic proximity in narrow-domain task spaces — requiring a lower threshold (0.80) and a rubric-overlap check that the paper does not specify.
