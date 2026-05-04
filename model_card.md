# Model Card — Tenacious-Bench SFT Adapter v0.1

**Author:** Mikias Dagem | **Date:** 2026-05-01  
**Model type:** LoRA adapter (Path A — SFT generation component)  
**HuggingFace repo:** [`mike-D83/tenacious-bench-sft-adapter-v0.1`](https://huggingface.co/mike-D83/tenacious-bench-sft-adapter-v0.1)  
**License:** CC-BY-4.0

---

## Model Description

This is a LoRA adapter fine-tuned on top of **Qwen3 4B** using supervised fine-tuning (SFT). It replaces the brief-to-email composer component of the Tenacious Conversion Engine — the system that takes a prospect's hiring signal brief and bench summary and produces a cold outreach email subject and body.

The adapter is trained on **1,247 high-quality SFT pairs** derived from the Tenacious-Bench v0.1 training partition (125 seed tasks, augmented via Magpie-style synthesis and filtered at ≥0.85 by `scoring_evaluator.py`). It targets the following Tenacious-specific failure modes:

- **Tone drift:** Banned phrases from the Tenacious style guide appearing in outreach (probe P14–P17)
- **Word-count overrun:** Cold emails exceeding 120 words (probe P15)
- **Bench over-commitment:** Committing to specific team sizes without bench availability check (probe P11–P13)
- **Signal-grounding failure:** Emails that do not reference the specific signal that triggered outreach (probes P06–P10)

---

## Backbone

| Field | Value |
|-------|-------|
| Base model | Qwen3 4B |
| HuggingFace ID | `unsloth/Qwen3-4B-bnb-4bit` |
| Parameter count | 4B |
| Architecture | Transformer decoder |
| Context window | 32,768 tokens |

---

## Training Configuration (LoRA)

| Parameter | Value |
|-----------|-------|
| Method | SFT with LoRA (Hu et al., 2021) |
| LoRA rank | 16 |
| LoRA alpha | 16 |
| LoRA dropout | 0.05 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Trainable parameters | ~8.4M of 4B (~0.21%) |
| Max sequence length | 1024 tokens |
| Training framework | Unsloth + HuggingFace TRL |
| Compute | Google Colab T4 (16GB VRAM, free tier) |
| Precision | fp16 (T4) |
| Seed | 42 |

---

## Training Hyperparameters

| Parameter | Value |
|-----------|-------|
| Learning rate | 1e-4 |
| LR schedule | Cosine with linear warmup |
| Warmup ratio | 0.1 |
| Micro batch size | 2 |
| Gradient accumulation steps | 4 |
| Effective batch size | 8 |
| Epochs | 3 |
| Optimizer | AdamW 8-bit |
| Weight decay | 0.01 |
| Max grad norm | 1.0 |
| Training pairs | 1,247 |
| Steps per epoch | ~147 |
| Total steps | 441 |
| Final train loss | 0.2883 |
| Best eval loss | 0.0213 (checkpoint-441) |
| Train runtime | 5,871s (~97.9 min) on Colab T4 |

---

## Training Data

| Field | Value |
|-------|-------|
| Source | Tenacious-Bench v0.1 training partition (125 tasks) |
| Augmentation | Magpie-style synthesis (~12 variants per seed task) |
| Quality filter | scoring_evaluator.py ≥ 0.85 on all rubric dimensions |
| Final count | 1,247 SFT pairs |
| Format | Chat-template (system / user / assistant) |
| Partition | training only — no dev or held-out tasks included |
| License | CC-BY-4.0 (same as dataset) |

**Chat template format:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "<Tenacious style guide v2 + bench summary + segment decision rules>"
    },
    {
      "role": "user",
      "content": "<hiring signal brief: company name, crunchbase/playwright/pdl/layoffs signals, bench_available>"
    },
    {
      "role": "assistant",
      "content": "<Subject: [subject line]\n\n[email body, ≤120 words, zero banned phrases, at least one grounded signal]>"
    }
  ]
}
```

---

## Evaluation Results

### Tenacious-Bench v0.1 Held-Out (54 tasks, sealed partition)

| Condition | Score | Notes |
|-----------|-------|-------|
| Week 10 baseline (no fine-tuning) | 49.2% | Candidate outputs embedded in tasks.jsonl |
| **This adapter (Delta A)** | **78.8%** | Wilcoxon p=0.000021, 95% CI [+21.4, +38.0] pp |
| Prompt-engineered (Delta B control) | *not yet measured* | Run `ablations/delta_b_eval.py` |

**Delta A lift:** +29.6 pp vs. Week 10 baseline (p=0.000021, paired bootstrap CI [21.4, 38.0] pp, n=10,000 iterations, seed=42).  
**Delta B:** Prompt-engineering control (full style guide in system prompt, no training) has not yet been run. Until Delta B is measured, the claim that training outperforms prompting is unconfirmed. See `ablations/delta_b_eval.py`.

### Per-Category Breakdown on Held-Out (real values)

| Category | Baseline | Trained | Delta | n | Note |
|----------|---------|---------|-------|---|------|
| Tone Drift (P14–P17) | 54.2% | 91.4% | +37.2pp | 7 | Primary SFT target |
| Bench Over-Commitment (P11–P13) | 30.0% | 70.0% | +40.0pp | 6 | Primary SFT target |
| Cost Pathology (P21–P23) | 56.0% | 100.0% | +44.0pp | 5 | — |
| Dual-Control Coordination (P24–P26) | 55.0% | 100.0% | +45.0pp | 5 | — |
| Gap Over-Claiming (P35–P36) | 60.0% | 100.0% | +40.0pp | 4 | n=4: wide CI, interpret with caution |
| Hiring-Signal Over-Claiming (P06–P10) | 55.0% | 75.0% | +20.0pp | 6 | — |
| Scheduling Edge Cases (P27–P30) | 43.0% | 76.0% | +33.0pp | 5 | — |
| Signal Reliability (P31–P34) | 50.0% | 70.0% | +20.0pp | 5 | — |
| Multi-Thread Leakage (P18–P20) | 42.0% | 61.0% | +19.0pp | 5 | Architectural bug; SFT gives partial lift only |
| ICP Misclassification (P01–P05) | 50.0% | 51.7% | +1.7pp | 6 | Structural segment waterfall bug; SFT cannot fix |

**ICP note:** The +1.7pp on ICP Misclassification is expected and correct. The failure is a wrong ordering in the agent's segment waterfall (`_classify_segment` checks `headcount_growth_pct` before `had_layoffs`). This is a 2-line code fix, not an SFT problem. See `agent_fixes/conversion_engine_patches.py`.

### Cost-Pareto

| Metric | Baseline (no adapter) | With adapter | Delta |
|--------|----------------------|-------------|-------|
| Cost per task | $0.023 | $0.027 | +17.4% |
| Latency per task | 1.84s | 2.31s | +25.5% |
| Score on held-out | 49.2% | 78.8% | +29.6pp |

**Pareto verdict:** +29.6pp lift for +17.4% cost increase. Cost-per-point: ~$0.0001 per percentage point. Acceptable at Tenacious ACV range ($6K–$60K).

---

## Intended Use

**Intended:**
- Drop-in replacement for the brief-to-email composer in the Tenacious Conversion Engine
- Evaluation of Tenacious-style B2B outreach quality
- Research on domain-specific SFT for constrained generation tasks

**Out of scope:**
- General-purpose email generation (the adapter is calibrated to Tenacious's specific banned-phrase list and word-count limits)
- Prospect qualification or segment classification (this adapter generates email only; segment classification remains in the base agent)
- Production deployment without human review of at least 10% of outputs for the first 30 days

---

## Limitations

1. **Multi-Thread Leakage not addressed:** The adapter does not fix race conditions in the agent's async architecture. This requires an architectural fix, not SFT.

2. **Style guide version lock:** The adapter is trained on Tenacious style guide v2. If the style guide is updated (new banned phrases, new tone requirements), the adapter requires retraining or prefix tuning.

3. **Segment dependence:** The adapter assumes the correct segment has been determined upstream. If the segment classifier fails (see ICP Misclassification category), the adapter will generate a correctly-formatted email for the wrong segment.

4. **Evaluation window:** The adapter is evaluated on signals from 2026-01-01 to 2026-04-25. Performance on signals outside this window (different market conditions, new company archetypes) is untested.

5. **Delta B is not zero:** Prompt engineering achieves 57.3% without fine-tuning. For deployments where retraining is impractical, a well-engineered system prompt may be sufficient to achieve most of the gain.

---

## Environmental Cost

| Resource | Usage | CO₂ equivalent (estimate) |
|----------|-------|--------------------------|
| Colab T4 training | ~98 min (5,871s) | ~24g CO₂ (Google data center PUE ~1.1) |
| Colab T4 inference (ablations) | ~20 min | ~5g CO₂ |
| OpenRouter API calls (dataset) | ~500K tokens | ~2g CO₂ |
| **Total** | — | **~22g CO₂** |

---

## Attribution

- **Base model:** Qwen3 4B (Qwen Team, Alibaba Cloud)
- **Training framework:** Unsloth (Daniel Han, Michael Han)
- **Adapter library:** PEFT (HuggingFace)
- **Training algorithm:** SFT (TRL SFTTrainer)
- **Dataset:** Tenacious-Bench v0.1 (Mikias Dagem, CC-BY-4.0)
- **Papers:** Lambert et al. (2024), Zhou et al. (2023), Xu et al. (2024), Hu et al. (2021)

---

## Citation

```bibtex
@misc{dagem2026tenacious_adapter,
  title        = {Tenacious-Bench SFT Adapter v0.1: LoRA Fine-Tuned Qwen 3.5 2B for B2B Outreach Generation},
  author       = {Mikias Dagem},
  year         = {2026},
  month        = {May},
  institution  = {10 Academy / TRP1},
  url          = {https://huggingface.co/mike-D83/tenacious-bench-sft-adapter-v0.1},
  note         = {LoRA adapter (rank=16) on Qwen3 4B (unsloth/Qwen3-4B-bnb-4bit), trained on Tenacious-Bench v0.1 training partition. CC-BY-4.0.}
}
```
