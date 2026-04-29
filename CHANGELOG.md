# Changelog — Tenacious-Bench

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1] — 2026-04-29 (Interim Submission — Acts I & II)

### Added

#### Act I: Probe Library & Evaluation Framework
- **probe_library.md** — 36 probes across 10 failure categories
  - P01–P05: ICP Misclassification (5 probes)
  - P06–P10: Hiring-Signal Over-Claiming (5 probes)
  - P11–P13: Bench Over-Commitment (3 probes)
  - P14–P17: Tone Drift (4 probes)
  - P18–P20: Multi-Thread Leakage (3 probes)
  - P21–P23: Cost Pathology (3 probes)
  - P24–P26: Dual-Control Coordination (3 probes)
  - P27–P30: Scheduling Edge Cases (4 probes)
  - P31–P34: Signal Reliability (4 probes)
  - P35–P36: Gap Over-Claiming (2 probes)

- **failure_taxonomy.md** — 10 failure categories ranked by business-cost impact
  - Ranked from CRITICAL (Bench Over-Commitment: $6,600/mo) to MEDIUM (Cost Pathology: $94/mo)
  - Systemic fix priorities for each category

- **audit_memo.md** — 600-word gap analysis
  - 7 structural gaps between τ²-Bench retail and Tenacious domain
  - Justifies need for Tenacious-Bench

- **schema.json** — Task schema + 3 annotated example tasks
  - Full schema definition with all required fields
  - TB-0001 (ICP Misclassification), TB-0091 (Tone Drift), TB-0142 (Bench Over-Commitment)

- **scoring_evaluator.py** — Machine-verifiable scorer (zero human in loop)
  - Deterministic rubric evaluation
  - CLI interface for batch scoring

- **methodology.md** — Path A declaration & justification
  - Path A: SFT of brief-to-email composer on Qwen 3.5 2B with LoRA
  - Contamination prevention: N-gram, embedding, time-shift checks
  - Inter-rater agreement: 30-task self-agreement matrix (≥ 80%)

#### Act II: Dataset & Validation
- **tenacious_bench_v0.1/** — 250-task dataset
  - 125 training tasks (50%)
  - 75 dev tasks (30%)
  - 50 held-out tasks (20%, gitignored)
  - Stratified by category and source_mode

- **datasheet.md** — Gebru + Pushkarna documentation (7 sections)
  - Motivation, composition, collection, preprocessing, uses, distribution, maintenance

- **contamination_check.json** — Validation results
  - N-gram overlap: 0 overlaps (all 50 held_out tasks pass)
  - Embedding similarity: max 0.82 (all 50 held_out tasks pass)
  - Time-shift verification: all 250 tasks pass

- **inter_rater_agreement.md** — 30-task self-agreement matrix
  - Overall agreement: 90% (all dimensions ≥ 80%)

- **synthesis_memos/** — 2 of 4 common synthesis memos
  - synthetic_data_best_practices.md
  - llm_as_judge_survey.md

- **cost_log.md** — Cost transparency
  - Total cost for Acts I & II: $47.32 USD

#### Documentation
- **TRP1_WEEK_ONE_INTERIM_SUBMISSION.md** — Comprehensive submission report
- **TASK_COMPLETION_CHECKLIST.md** — Detailed task verification
- **SUBMISSION_SUMMARY.md** — Executive summary
- **DELIVERABLES_OVERVIEW.md** — Quick reference guide
- **INDEX.md** — Complete file index
- **FINAL_SUBMISSION_REPORT.txt** — Text summary

#### Configuration
- **.gitignore** — Excludes held_out partition and common artifacts
- **requirements.txt** — Python dependencies
- **CHANGELOG.md** — This file

### Metrics

- **Total tasks:** 250
- **Categories:** 10
- **Probes:** 36
- **Baseline (Week 10 on dev):** 49.1%
- **Inter-rater agreement:** 90% (all dims ≥ 80%)
- **Contamination checks:** 100% pass
- **Cost:** $47.32 USD

### Known Limitations

- **Domain-specific:** Only measures Tenacious-specific failure modes
- **Signal availability:** Assumes access to Crunchbase, Playwright, PDL, Layoffs.fyi signals
- **Temporal anchoring:** Tasks reference specific dates (2026-01-01 to 2026-04-25)
- **Deterministic scoring:** All rubrics are deterministic; cannot measure subjective quality

---

## [Unreleased] — Future Versions

### Planned for v0.2

- [ ] Expand dataset to 500 tasks
- [ ] Add 5 new failure categories
- [ ] Improve rubric clarity based on user feedback
- [ ] Add human review for 10% of tasks

### Planned for v1.0

- [ ] Final dataset with 1,000 tasks
- [ ] Training run results (Path A: SFT on Qwen 3.5 2B)
- [ ] Ablation studies (Delta A, Delta B, Delta C)
- [ ] Publication to HuggingFace Hub
- [ ] Technical blog post
- [ ] GitHub issue on τ²-Bench repo

### Planned for v2.0

- [ ] Multi-domain support (not just Tenacious)
- [ ] Preference-based scoring (pairwise comparisons)
- [ ] Process reward model (PRM) training
- [ ] Real-time evaluation API

---

## Contributing

To contribute to Tenacious-Bench:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a Pull Request

### Contribution Guidelines

- Follow the existing code style (PEP 8 for Python)
- Add tests for new features
- Update documentation
- Ensure all tests pass before submitting PR

---

## License

Tenacious-Bench is licensed under the Creative Commons Attribution 4.0 International (CC-BY-4.0) license.

See LICENSE file for details.

---

## Citation

```bibtex
@dataset{dagem2026tenacious,
  title        = {Tenacious-Bench v0.1: A Sales Agent Evaluation Dataset for B2B Outreach Failure Modes},
  author       = {Mikias Dagem},
  year         = {2026},
  month        = {April},
  institution  = {10 Academy / TRP1},
  license      = {CC-BY-4.0},
  note         = {250 tasks across 10 failure categories derived from the Tenacious Conversion Engine probe library. Interim submission (Acts I & II) completed 2026-04-29.}
}
```

---

## Contact

**Author:** Mikias Dagem  
**Email:** mikias@10academy.org  
**Challenge:** TRP1 — Tenacious Conversion Engine Evaluation Dataset

---

*End of Changelog*
