# Synthesis Memo: Datasheets for Datasets + Data Cards

**Author:** Mikias Dagem | **Date:** 2026-05-01  
**Papers:** Gebru et al. (2021) *Datasheets for Datasets*; Pushkarna et al. (FAccT 2022) *Data Cards: Purposeful and Transparent Dataset Documentation*  
**Application:** Tenacious-Bench v0.1 datasheet design and documentation standard

---

## Core Argument of Each Paper

### Gebru et al. (2021) — Datasheets for Datasets

Gebru et al. observe that the electronics industry documents every component with a datasheet specifying intended use, operating conditions, and failure modes — but the ML community ships datasets with no equivalent transparency. Their proposed template covers seven mandatory sections: Motivation, Composition, Collection Process, Preprocessing/Cleaning/Labeling, Uses, Distribution, and Maintenance. The authors argue that without this documentation, ML practitioners cannot assess dataset fitness, and harms from misuse are predictable but preventable.

The paper is descriptive and prescriptive: it documents what *should* be in a datasheet but stops short of specifying how detailed each section must be, leaving implementers to calibrate depth to context.

### Pushkarna et al. (FAccT 2022) — Data Cards

Data Cards extends the Gebru framework with three structural innovations:

1. **Layered detail (telescopic, periscopic, microscopic):** A telescopic view gives a one-paragraph summary; periscopic adds the methodology; microscopic exposes every construction decision. This lets different readers (executives, researchers, auditors) find the level of detail they need without reading the full document.

2. **Use-case specificity:** Rather than describing a dataset generically, Data Cards require the author to specify *intended* use cases and *out-of-scope* uses with rationale. This shifts documentation from descriptive to evaluative.

3. **Field-level granularity:** Data Cards push documentation down to the level of individual fields (what does `confidence: 0.85` mean? how was it measured?), not just dataset-level descriptions.

---

## Application to Tenacious-Bench v0.1

### What I adopted from Gebru et al.

The seven-section structure is preserved verbatim in `datasheet.md`:
- **Motivation:** Why Tenacious-Bench exists (τ²-Bench retail gap, Tenacious-specific failure modes)
- **Composition:** 250 tasks, 10 categories, 4 source modes, 3 partitions, difficulty distribution
- **Collection Process:** The four authoring modes with share percentages and model rotation policy
- **Preprocessing/Cleaning/Labeling:** LLM-as-judge filter (≥4/5 on 3 dimensions), contamination checks
- **Uses:** Intended (training, evaluation, ablations) and out-of-scope (production filtering without human review)
- **Distribution:** CC-BY-4.0 license, HuggingFace Hub, held-out sealing protocol
- **Maintenance:** Version roadmap (v0.2 planned after Week 11 leaderboard)

### What I adopted from Pushkarna et al.

The layered detail structure is applied in `datasheet.md` Section 2 (Composition):
- *Telescopic:* "250 tasks across 10 failure categories, three partitions."
- *Periscopic:* Per-category counts, source mode distribution, difficulty breakdown.
- *Microscopic:* Field-level definitions for `crunchbase_signal.confidence`, `playwright_signal.page_timestamp_days_ago`, and the five `bench_available` role slots — because these fields are what the scoring rubric checks, and their meaning is non-obvious.

Use-case specificity from Data Cards is applied in the Uses section: Tenacious-Bench is explicitly *out of scope* for evaluating general B2B sales agents not trained on Tenacious's specific style guide, because the banned-phrase list and word-count limits are Tenacious-internal constraints.

---

## Where I Disagree with the Papers

### Disagreement with Gebru et al.: The Maintenance section is structurally underspecified

Gebru et al. include "Maintenance" as a section but provide only three template questions (who maintains it? how do users contact the team? will it be updated?). For an evaluation benchmark — unlike a training dataset — maintenance has a qualitatively different requirement: **held-out integrity**. A dataset used for training can be updated freely; a benchmark's held-out partition cannot be changed without invalidating all prior scores.

Gebru's template does not address this distinction. Tenacious-Bench `datasheet.md` adds a "Held-Out Integrity" subsection under Maintenance that specifies: (1) the held-out tasks are never modified after v0.1 publication, (2) new tasks are added in a separate held-out extension at v0.2, and (3) any model trained on dev tasks is excluded from the held-out leaderboard by self-report.

*Evidence for the gap:* The contamination-check protocol in `contamination_check.json` addresses training-to-held-out leakage at creation time, but the Gebru template has no mechanism for post-publication leakage (e.g., a model trained on benchmark results that are publicly available). The held-out integrity subsection fills this gap.

### Disagreement with Pushkarna et al.: Field-level granularity is impractical for dynamic signal fields

Pushkarna et al. recommend documenting every field at the microscopic level. For static fields (task_id, category, difficulty) this is straightforward. For dynamic signal fields (`crunchbase_signal`, `playwright_signal`, `pdl_signal`, `layoffs_signal`), microscopic documentation would require specifying the exact API response schema from Crunchbase, PDL, and layoffs.fyi at the time of dataset creation — information that changes as APIs evolve and that Tenacious treats as partially confidential.

The practical compromise in `datasheet.md`: signal fields are documented to the *periscopic* level (what each field represents, what confidence scores mean, what date windows are used), with a footnote that the microscopic schema is available in `schema.json` for users who need it. This preserves reproducibility without exposing API-level detail that would be stale within months.

---

## Key Design Decision Influenced by These Papers

The decision to include a separate `inter_rater_agreement.md` rather than embedding agreement scores in the datasheet was influenced by both papers. Gebru et al. mention labeling in Section 4 but do not specify how to report labeler agreement. Pushkarna et al. push for field-level granularity but do not give a template for agreement matrices.

The explicit 30-task IRA protocol with per-dimension agreement scores (93% segment, 97% banned-phrases, 85% bench-commitment) addresses a gap in both frameworks: benchmark datasets need to document *scorer* agreement, not just labeler agreement, because the scoring rubric is itself a research artifact.

---

## One-Sentence Summary

Gebru gives the sections; Pushkarna gives the layering; neither gives adequate guidance for benchmark-specific integrity constraints (held-out sealing, scorer IRA, post-publication leakage), so Tenacious-Bench adds those explicitly rather than leaving them implicit.
