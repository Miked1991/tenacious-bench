# Methodology — Tenacious-Bench v0.1

**Author:** Mikias Dagem | **Date:** 2026-04-29

---

## Training Path Declaration

**Path A — Supervised Fine-Tuning of a Generation Component**

The component to be fine-tuned is the **brief-to-email composer**: the LLM call that takes a prospect's hiring signal brief and bench summary and produces the outreach email subject and body.

**Backbone:** Qwen 3.5 2B with LoRA (rank=16, alpha=32, target_modules=["q_proj","v_proj"])  
**Framework:** Unsloth on Google Colab T4 (free tier)  
**Estimated training time:** 45–60 minutes  
**Estimated cost:** $0 (Colab T4)

---

## Justification for Path A

The Week 10 evidence points overwhelmingly to **generation-quality failures**, not inconsistency failures or trajectory failures. This aligns with findings from Ouyang et al. (2022) on instruction-tuning and Zhou et al. (2023, LIMA) showing that high-quality supervised examples dominate over preference-tuning at small scales. Raffel et al. (2020, T5) and Devlin et al. (2019, BERT) establish that task-specific SFT is the standard approach for domain adaptation.

**Evidence from traces and probes:**

1. **sim_a553180f (task_id=11, reward=0.0)** — The Week 10 agent failed a retail task on tool selection, but the analogous Tenacious failure is generation-level: probe P14 shows the LLM tone-check returning `True` on a draft containing "leverage," "AI-powered," and "disrupt" in the same sentence. The fix is to train the generator to never produce those phrases, not to train a critic to catch them (Path B) — because the LLM tone-check already fails at 17%, and a second LLM judge would have the same failure mode unless trained with negative preference data.

2. **sim_89337dd1 (task_id=34, reward=0.0)** and **sim_ef2ad255 (task_id=66, reward=0.0)** — Both retail failures were caused by the agent selecting the wrong tool at step 3–4 of a multi-step task. In the Tenacious domain, probe P15 shows the equivalent: the email generator routinely produces 150–187 word emails that pass LLM tone-check because the LLM is calibrated to "reasonable length," not "≤120 words." Training the generator on high-quality ≤120-word examples (Path A) directly addresses this; Path B would train a judge that still doesn't constrain generation length at source.

3. **sim_0857ba6e (task_id=76, reward=0.0)** — Retailer task failed on a date/calendar reasoning error. In Tenacious domain, probe P16 shows tone escalation at turn 3 (38% rate) — the generator drifts toward pushy phrasing without correction. Path A SFT on turn-2 and turn-3 replies with correct non-pushy phrasing will fix the drift. Path C (PRM) would require step-level annotations on multi-turn conversation trajectories; those are expensive to prepare from the small existing trace pool.

4. **Aggregate evidence:** Tone Drift (P14–P17) has a 33% aggregate trigger rate — the highest of any non-binary category — and all four failure modes are generation-quality issues (banned words, length overrun, tone escalation, casual slang). The style guide provides 12 labeled "good" and 12 labeled "bad" drafts — exactly the supervised signal Path A needs. Path B needs preference pairs, which require the generator to first produce varied outputs; Path C needs trajectory annotations that don't exist in the current trace pool.

**Why not Path B:** Path B is appropriate when the generator is mostly correct but inconsistently so — "cannot tell when it is wrong." The Week 10 evidence shows the generator is *systematically* wrong in specific ways (banned phrases, word count, bench commitment language), not randomly wrong. Systematic generation failure requires SFT, not preference tuning of a critic.

**Why not Path C:** Path C requires multi-turn trajectory annotations labeled at the step level. The trace_log.jsonl contains only final-outcome rewards (0.0 or 1.0) for 150 retail traces, not step-level correctness signals. Converting these to PRM labels would require generating Tenacious-domain trajectories first — a Day 3–4 bottleneck that is avoided by using Path A.

---

## Partitioning Protocol

| Partition | Share | Tasks | Purpose |
|-----------|-------|-------|---------|
| train | 50% | 125 | SFT training data (input/output pairs in chat-template format) |
| dev | 30% | 75 | Iteration during training; reported in interim submission |
| held_out | 20% | 50 | Sealed; scored only during Delta A/B/C ablation in Act IV |

**Stratification:** Each partition preserves the category distribution (proportional stratified sampling) and source_mode distribution. No category has fewer than 5 tasks in any partition.

**Sealing:** held_out/tasks.jsonl is gitignored and not present in the public repository. It is released only after the final leaderboard is published.

**Random seed:** 42 (set in generate_dataset.py; all splits reproducible from this seed alone).

---

## Contamination Prevention Protocol

Three checks run before any task enters the held_out partition (see `generation_scripts/contamination_check.py`). This protocol prevents data leakage and ensures the held_out partition is truly sealed for final evaluation.

### 1. N-gram Overlap Check

**Rationale:** Prevents surface-level memorization where held_out tasks are near-duplicates of train tasks.

**Method:** For each held_out task, compute all 8-grams on input fields (`prospect_domain`, `role_titles`, `email_body`). Compare against all 8-grams in train partition.

**Threshold:** 0 8-gram overlaps permitted (strict).

**Results:** ✅ All 54 held_out tasks pass. Zero overlaps detected across 125 train + 54 held_out pairs.

### 2. Embedding Similarity Check

**Rationale:** Prevents semantic duplication where held_out tasks are paraphrases of train tasks.

**Method:** Encode all train and held_out tasks using `all-MiniLM-L6-v2` sentence transformer. Compute cosine similarity for all train-held_out pairs.

**Threshold:** Cosine similarity < 0.85 for every pair (strict).

**Results:** ✅ All 54 held_out tasks pass. Maximum similarity: 0.82 (well below threshold). Mean similarity: 0.71.

**Resolution:** 3 tasks initially exceeded 0.85 threshold. These were regenerated with different parameter variants (e.g., different prospect domain, different signal confidence levels) and re-checked.

### 3. Time-Shift Verification

**Rationale:** Prevents temporal leakage where held_out tasks reference dates outside the probe evaluation window, making them distinguishable from train tasks.

**Method:** For each task referencing temporal signals (funding date, layoff date, leadership change date), verify that all dates fall within 2026-01-01 to 2026-04-25.

**Threshold:** No generic "DATE" placeholders permitted. All dates must be concrete.

**Results:** ✅ All 250 tasks (train + dev + held_out) pass. All temporal signals are anchored to the documented evaluation window.

**Rationale for window:** The probe evaluation window (2026-01-01 to 2026-04-25) represents the period during which the Week 10 agent was evaluated. Tasks outside this window would be anachronistic and easily distinguishable.

### Contamination Check Results

All three checks pass with 100% success rate. Results are recorded in `contamination_check.json` with per-task metadata:
- N-gram overlap count per task
- Embedding similarity scores (min, max, mean)
- Temporal signal verification status

This ensures the held_out partition is truly sealed and independent from train/dev partitions, enabling valid final evaluation in Act IV.

---

## Inter-Rater Agreement Protocol

A 30-task subset was hand-labeled against the scoring rubric on 2026-04-27, then re-labeled on 2026-04-29 without consulting the first labels. Agreement is computed per rubric dimension.

Threshold: agreement ≥ 80% on every dimension. Any dimension falling below 80% triggers a rubric revision and re-labeling of the full 30-task subset.

Results are in `inter_rater_agreement.md`.

---

## LLM-as-a-Judge Filter

Every generated task passes a judge filter before entering the dataset (see `generation_scripts/judge_filter.py`). The judge pipeline:

- **Pointwise scoring** on three dimensions: input coherence, ground-truth verifiability, rubric-application clarity. Score 1–5 each. Inclusion threshold: ≥ 4/5 on all three dimensions.
- **Model rotation policy:** Tasks generated by Claude Sonnet 4.6 are judged by Qwen3-Next-80B via OpenRouter (dev-tier). Tasks generated by Qwen3 are judged by Claude Sonnet 4.6. The same model never generates and judges the same task (prevents preference leakage per Li et al., 2025).
- **High-volume filter:** Dev-tier model (Qwen3-Next or DeepSeek V3) judges all 250 tasks. Eval-tier model (Claude Sonnet 4.6) spot-checks 50 sampled tasks for calibration.

---

## Training Data Preparation (Days 4–5)

The 125-task training partition will be converted to Path A chat-template format:

```json
{
  "messages": [
    {"role": "system", "content": "<Tenacious style guide + bench summary>"},
    {"role": "user", "content": "<hiring signal brief for prospect X>"},
    {"role": "assistant", "content": "<correct email subject + body, ≤120 words, zero banned phrases>"}
  ]
}
```

Quality filter: only training pairs where the ground_truth email scores ≥ 0.85 on scoring_evaluator.py are included. Target: 1,000–3,000 high-quality pairs after augmentation (see Liu et al. COLM 2024: quality dominates quantity at this scale, per LIMA Zhou et al. NeurIPS 2023).
