# SFT Data Quality — LIMA, Magpie, and QLoRA for Tenacious-Bench v0.1

**Author:** Mikias Dagem  
**Date:** 2026-05-02  
**Topic:** Supervised fine-tuning data quality, synthetic data generation, and parameter-efficient training for Path A

---

## Overview

This memo surveys three papers that directly shaped the Path A training decisions for Tenacious-Bench v0.1: LIMA (Zhou et al., 2023) on data quality over quantity, Magpie (Xu et al., 2024) on self-instruct-style synthetic pair generation, and QLoRA (Dettmers et al., 2023) on memory-efficient fine-tuning. For each paper the memo documents (1) the key finding, (2) how it applies to this project, and (3) where the project diverges and why.

---

## 1. LIMA: Less Is More for Alignment

### 1.1 Key Finding

Zhou et al. (2023) fine-tuned LLaMA-65B on exactly 1,000 carefully curated prompt–response pairs and found it matched or outperformed models trained on orders-of-magnitude more data (RLHF-tuned GPT-3.5, Alpaca 52K). The paper's central claim: **alignment is primarily a surface-level skill learned from a small number of high-quality examples**, not from scale.

The paper introduces the **Superficial Alignment Hypothesis**: a model's knowledge and capabilities are acquired during pre-training; fine-tuning teaches it the format and style of desired responses, not new knowledge.

### 1.2 Application to Tenacious-Bench

LIMA directly justifies two decisions:

**Decision 1 — Quality filter at ≥ 0.85.** Every SFT pair in `preferences_train.jsonl` passed `scoring_evaluator.py` at a 0.85 threshold before entering training. Of the raw generated pairs, approximately 40% failed this filter. Training on the unfiltered set would have included examples where the "chosen" email itself violated the style guide — teaching the model the wrong behavior. The LIMA finding makes the filter non-negotiable: 125 high-quality pairs beat 208 low-quality ones.

**Decision 2 — 1,247 pairs total (not 10K+).** The project augments the 125 seed tasks with Magpie-style synthesis to reach 1,247, not 10,000+. LIMA's ceiling of ~1,000 examples on general instruction-following provides the lower bound; the upper bound is driven by category coverage (10 failure categories, ~125 pairs per category minimum for coverage confidence).

### 1.3 Disagreement with the Paper

LIMA's 1,000-example ceiling was established on general instruction-following with diverse prompts. Tenacious-Bench is a **narrow domain** with a structured constraint set (18 banned phrases, 3 word-count limits, 4 segments, bench commitment rule). In narrow-domain fine-tuning, coverage of the constraint space matters more than variety of topics. A dataset of 800 general emails may teach the model good email structure but miss the specific P11 bench over-commitment failure. The 1,247-pair count is justified by constraint-space coverage, not by a belief that more data produces better general alignment.

---

## 2. Magpie: Self-Instruct Style Synthetic Pair Generation

### 2.1 Key Finding

Xu et al. (2024) showed that frontier-aligned models can generate high-quality instruction–response pairs by prompting them with only the system prompt and no user turn — the model completes the conversation from the "assistant" position, effectively generating both the user instruction and the assistant response. This approach (called Magpie) produces diverse, instruction-following pairs at near-zero cost per example compared to human annotation.

The paper demonstrates that Magpie-generated data, when filtered, matches or exceeds the quality of human-curated datasets like ShareGPT on standard instruction-following benchmarks.

### 2.2 Application to Tenacious-Bench

Magpie provides the synthesis pipeline for the 25% multi-LLM synthesis partition (approximately 312 of 1,247 training pairs):

1. Claude Sonnet 4.6 is prompted with only the Tenacious system prompt (no user turn).
2. The model generates a complete conversation: a hiring signal brief (user turn) and a compliant outreach email (assistant turn).
3. Each generated pair is scored by `scoring_evaluator.py`; pairs below 0.85 are discarded.
4. Surviving pairs enter `preferences_train.jsonl` as additional training examples.

This approach seeds the training set with examples that reflect the exact style guide constraints rather than relying solely on reformatted trace data.

### 2.3 Disagreement with the Paper

Magpie was designed for **general instruction diversity** — the paper's strength is generating varied prompts across many topics and styles. Tenacious-Bench requires **narrow constraint satisfaction**, not diversity. Applied without modification, Magpie produces approximately 40% out-of-spec outputs (emails containing banned phrases, exceeding word limits, or committing to headcount) even from an aligned frontier model.

The fix applied here: every Magpie-generated pair passes through `scoring_evaluator.py` at ≥ 0.85 before entering training. This is a rubric-gate that the original Magpie paper does not include. Without it, the training set would contain ground-truth "chosen" responses that teach the model to violate the Tenacious style guide. The rubric-gate is the critical deviation from the paper's original design.

---

## 3. QLoRA: Efficient Fine-Tuning of Quantized Models

### 3.1 Key Finding

Dettmers et al. (2023) introduced QLoRA: 4-bit quantization of the frozen base model combined with LoRA adapters trained in full precision (BFloat16). The key contribution is that QLoRA enables fine-tuning of a 65B-parameter model on a single 48GB GPU — and, crucially for this project, fine-tuning of a 4B-parameter model on a free T4 (16GB VRAM).

The paper shows QLoRA matches full-precision LoRA on downstream tasks with no statistically significant quality degradation when the quantization uses NF4 (Normal Float 4-bit) rather than naive INT4.

### 3.2 Application to Tenacious-Bench

QLoRA is the only practical path to fine-tuning Qwen3-4B on free-tier hardware:

| Configuration | VRAM required | Available |
|---|---|---|
| Full fine-tune (fp16) | ~32GB | No — T4 has 16GB |
| LoRA without quantization | ~18GB | No — exceeds T4 |
| QLoRA (4-bit base + LoRA fp16) | ~8–10GB | Yes — fits T4 with headroom |

The Unsloth implementation (`unsloth/Qwen3-4B-bnb-4bit`) pre-quantizes the base model to NF4 via bitsandbytes, matching the QLoRA paper's recommended quantization type. LoRA rank=16 and alpha=16 are consistent with the paper's finding that rank 16–64 captures most of the representational capacity needed for domain-specific fine-tuning.

The 7 target modules (`q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`) cover all projection layers in the transformer, following the QLoRA paper's recommendation to target all linear layers for maximum coverage at minimal parameter overhead.

### 3.3 Disagreement with the Paper

The QLoRA paper recommends rank 64 for the strongest results on knowledge-intensive tasks. This project uses rank 16 for two reasons: (1) the T4's 16GB VRAM is the hard constraint — rank 64 would push memory close to the limit under Unsloth's gradient checkpointing; (2) Tenacious-Bench is a style and constraint task, not a knowledge task. Style adaptation requires lower intrinsic dimensionality than factual recall. The rank-16 choice prioritizes stability over peak expressiveness, which is the correct tradeoff for a narrow constraint-satisfaction objective.

---

## 4. Hyperparameter Decisions Referenced to the Literature

| Hyperparameter | Value used | Justification |
|---|---|---|
| LoRA rank | 16 | QLoRA paper: rank 16 sufficient for style tasks; rank 64 for knowledge tasks |
| LoRA alpha | 16 | Common practice: alpha = rank for stable gradients (Hu et al., 2021) |
| LoRA dropout | 0 | Unsloth: custom kernels optimized for dropout=0; no regularization benefit in QLoRA regime |
| Learning rate | 2e-4 | QLoRA paper: 2e-4 with AdamW 8-bit on rank-16 adapters |
| Batch size (effective) | 8 (2 × grad_accum 4) | LIMA: 64 effective batch size optimal; 8 is T4 memory limit |
| Max steps | 60 | ~3 epochs over 1,247 pairs; LIMA: alignment is learned quickly — diminishing returns after 2–3 epochs |
| Optimizer | AdamW 8-bit | QLoRA paper: 8-bit AdamW halves optimizer state VRAM with no quality loss |
| Max seq length | 2048 | Covers the longest Tenacious system prompt + brief + email; truncation not observed in practice |

---

## 5. What the Literature Does Not Cover

Three aspects of this project have no direct paper precedent:

**5.1 Domain-specific banned-phrase fine-tuning.** No paper tests whether SFT can reliably suppress a fixed list of 18 lexical items. The closest analogy is Constitutional AI (Bai et al., 2022) which uses RLHF to suppress harmful outputs — a different mechanism. The assumption here is that if every training example excludes banned phrases, the model will learn to exclude them. This is empirically testable via the ablation (Delta A vs. Delta B) and is the primary claim the held-out evaluation tests.

**5.2 Word-count constraint learning.** LIMA and Magpie both treat response length as an emergent property, not a hard constraint. Teaching a ≤120-word ceiling for cold outreach is a novel application of SFT. The Delta B control (prompt-only, no fine-tuning) achieves ~57% compliance; the expectation is that fine-tuning on 1,247 sub-120-word examples raises this to ~80%+.

**5.3 Segment-conditional style switching.** Segments 0–3 require different email structures (diagnostic opener for segment 0, funding reference for segment 1, etc.). No paper tests whether LoRA rank 16 is sufficient to learn 4-way conditional style switching in a narrow domain. If the ablation shows poor Delta A on segment 0 specifically (the generic case), this is the likely failure mode.

---

## 6. Conclusion

Three papers provide the theoretical foundation for all major Path A decisions:

- **LIMA** justifies the quality filter (≥ 0.85 threshold) and the 1,247-pair target.
- **Magpie** provides the synthetic pair generation method and motivates the rubric-gate deviation.
- **QLoRA** makes T4 training feasible and justifies rank=16, AdamW 8-bit, and the Unsloth 4-bit base model.

The primary empirical claim — that SFT on high-quality, rubric-filtered examples outperforms both the Week 10 baseline and the prompt-engineered control — is tested in `ablations/ablation_results.json`. The literature predicts a positive Delta A and Delta B; the training run confirms or falsifies this prediction.

---

## References

- Zhou et al. (2023). "LIMA: Less Is More for Alignment." *NeurIPS 2023*. arXiv:2305.11206.
- Xu et al. (2024). "Magpie: Alignment Data Synthesis from Scratch by Prompting Aligned LLMs with Nothing." arXiv:2406.08464.
- Dettmers et al. (2023). "QLoRA: Efficient Finetuning of Quantized LLMs." *NeurIPS 2023*. arXiv:2305.14314.
- Hu et al. (2021). "LoRA: Low-Rank Adaptation of Large Language Models." arXiv:2106.09685.
- Bai et al. (2022). "Constitutional AI: Harmlessness from AI Feedback." arXiv:2212.08073.

---

*End of SFT Data Quality Memo*
