# Audit Memo — What τ²-Bench Retail Fails to Grade

**Author:** Mikias Dagem | **Date:** 2026-04-29 | **Max:** 600 words

---

## The Gap in One Sentence

τ²-Bench retail measures whether an agent can complete shopping tasks (add to cart, track orders, apply coupons) on a scripted e-commerce environment. The Tenacious Conversion Engine is a B2B outreach agent that classifies prospects, fuses four async data signals, and composes personalized cold emails. These are structurally incompatible evaluation targets.

## What τ²-Bench Retail Cannot Grade

**1. Signal-confidence-aware language generation.** The Tenacious style guide requires the agent to use interrogative phrasing when signal confidence is below 0.7, and assertive phrasing only when confidence is above 0.7. τ²-Bench has no signal-confidence dimension. Traces sim_a553180f (task_id=11, reward=0.0) and sim_89337dd1 (task_id=34, reward=0.0) show the Week 10 agent failing retail tasks for reasons unrelated to this capability — the retail reward function cannot surface the probe P06 failure where a single stale job post (confidence=0.8 but timestamp=8 months ago) is over-claimed as "aggressive hiring" in 34% of runs.

**2. Prospect segment classification accuracy.** The agent's `_classify_segment()` function applies a waterfall of conditions. τ²-Bench never presents a classification decision; it presents cart-management tasks. Probe P01 shows the agent misclassifying bootstrapped companies as recently-funded in 23% of cases when Crunchbase confidence is 0.0 — a failure mode invisible to any retail benchmark. Trace sim_ef2ad255 (task_id=66, reward=0.0) and sim_0857ba6e (task_id=76, reward=0.0) are retail failures from an entirely different capability surface.

**3. Bench commitment accuracy.** Probe P11 shows 100% of segment=3 (hypergrowth) emails containing unqualified "scale rapidly" language when the bench has fewer than the implied engineers available. Probe P12 shows 100% failure when a niche specialty (quantum computing) is detected. τ²-Bench has no concept of capacity constraints or inventory commitments in a services business. Retail tasks require clicking buttons, not refusing to over-promise.

**4. Multi-source signal staleness detection.** Probe P32 shows 29% of companies whose last Crunchbase funding was 12–36 months ago receiving `recently_funded=True` because the LLM was delegated the recency judgment without a deterministic threshold. Probe P33 shows ~12% of PDL leadership changes being stale within 60 days. τ²-Bench cannot test this because it has no concept of temporal signal degradation.

**5. GDPR / multi-thread data leakage.** Probe P18 documents a 7% race-condition rate under concurrent async load where lead A's profile is read into lead B's context. Probe P20 shows 100% failure in bounce-plus-replay scenarios, where a suppressed lead still receives agent replies. Trace sim_19d13ac9 (task_id=92, reward=0.0) and sim_58d3c8bc (task_id=106, reward=0.0) are retail failures — τ²-Bench has no shared-state scenarios that would expose cross-lead contamination.

**6. Tenacious style guide compliance.** The style guide bans 18 specific phrases and enforces a 120-word cold-email limit. Probe P14 shows a 17% LLM tone-check false-pass rate for banned phrases; P15 shows 24% of emails exceeding the word limit despite passing tone-check. τ²-Bench scores tool-use success, not linguistic constraint satisfaction. Trace sim_f50f1801 (task_id=105, reward=0.0) cost $0.023 — 15% above average — matching the cost pathology pattern in P21.

**7. Timezone-aware scheduling.** Probe P27 shows 18% of EU prospects booked at local midnight; P29 shows 22% of US West Coast prospects booked at 6am Pacific. τ²-Bench has no scheduling component.

## What This Proves

The Week 10 agent achieved 72.7% on τ²-Bench retail (150 traces, all `domain=retail`). This number is meaningful for retail task completion and nothing else. The probe library documents 10 failure categories, 36 specific probes, and trigger rates of 7–100% on Tenacious-specific behaviors that τ²-Bench cannot observe. Tenacious-Bench v0.1 is built to make those failures measurable, statistically separable, and trainable.
