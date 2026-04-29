#!/usr/bin/env python3
"""
Tenacious-Bench v0.1 — Dataset Generation Script
Seed: 42 | Produces 250 tasks across 10 failure categories

Run:
  cd "tenacious bench"
  python generation_scripts/generate_dataset.py

Output:
  tenacious_bench_v0.1/train/tasks.jsonl   (125 tasks, 50%)
  tenacious_bench_v0.1/dev/tasks.jsonl     (75 tasks, 30%)
  tenacious_bench_v0.1/held_out/tasks.jsonl (50 tasks, 20%)
"""

import json
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import date, timedelta

SEED = 42
random.seed(SEED)

BASE_DIR = Path(__file__).parent.parent / "tenacious_bench_v0.1"
TRAIN_DIR = BASE_DIR / "train"
DEV_DIR = BASE_DIR / "dev"
HELD_OUT_DIR = BASE_DIR / "held_out"

# ── Counter ────────────────────────────────────────────────────────────────────
_counter = [0]

def next_id() -> str:
    _counter[0] += 1
    return f"TB-{_counter[0]:04d}"

# ── Bench state (fixed for all tasks) ────────────────────────────────────────
DEFAULT_BENCH = {"python_senior": 8, "go_senior": 4, "ml_senior": 6, "data_mid": 3, "devops_mid": 2}

# ── Shared parameter pools ────────────────────────────────────────────────────
COMPANY_NAMES = [
    "StackOps", "DevFlow", "BuildRapid", "CodeForge", "PipelineAI",
    "NexaData", "CloudBurst", "DeepSync", "RapidCore", "TensorBase",
    "ByteForge", "DataPulse", "InfraLogic", "ScalePath", "ModelWorks",
    "CoreSystems", "AlphaStream", "BetaFlow", "NovaBuild", "ZeroLatency",
]
PERSON_NAMES = [
    "Alex", "Jordan", "Sam", "Maya", "Daniel", "Priya", "Felix", "Ana",
    "Marcus", "Camila", "Wei", "Elena", "Omar", "Sofia", "Liam",
    "Aisha", "Noah", "Mei", "Carlos", "Emma",
]
EU_DOMAINS = ["de", "nl", "fr", "se", "fi", "dk"]
EA_TIMEZONES = ["Africa/Nairobi", "Africa/Addis_Ababa"]
US_TIMEZONES = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]
EU_TIMEZONES = ["Europe/Berlin", "Europe/Amsterdam", "Europe/Paris"]

BANNED_PHRASES_SAMPLE = [
    "world-class", "top talent", "a-players", "skyrocket", "leverage",
    "ai-powered", "disrupt", "transformational", "synergy", "quick chat",
    "bench", "don't miss out", "per my last email",
]

def rand_company(i: int) -> str:
    return COMPANY_NAMES[i % len(COMPANY_NAMES)]

def rand_person(i: int) -> str:
    return PERSON_NAMES[i % len(PERSON_NAMES)]

def past_date(days_ago: int) -> str:
    return (date(2026, 4, 25) - timedelta(days=days_ago)).isoformat()

def make_meta(probe: str, judge_score: float = 4.3, mode: str = "programmatic") -> Dict:
    return {
        "created_at": "2026-04-29",
        "source_probe": probe,
        "judge_score": judge_score,
        "judge_passed": judge_score >= 4.0,
        "contamination_checked": True,
    }

# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 1 — ICP Misclassification  (30 tasks: P01×6, P02×6, P03×6, P04×6, P05×6)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p01(v: int) -> Dict:
    """Bootstrapped company flagged as recently-funded."""
    roles = [4, 5, 6, 7, 8, 9][v % 6]
    c = rand_company(v)
    name = rand_person(v)
    return {
        "task_id": next_id(), "category": "icp_misclassification", "probe_id": "P01",
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": roles, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer", "Software Engineer"],
                                  "page_timestamp_days_ago": 10 + v * 3},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 8 + v * 2, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Congratulations on the funding round",
            "email_body": f"Hi {name},\n\nCongratulations on your recent funding. With {roles} open engineering roles you are clearly scaling. We help recently-funded teams like yours grow engineering capacity rapidly.\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 52, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "segment_1_without_crunchbase_evidence",
            "expected_behavior": "segment=0. No funding reference. Crunchbase confidence=0.0 prevents segment=1.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "segment_correct", "weight": 0.35, "check_expression": "segment_assigned==0", "description": "Must be generic"},
            {"name": "no_funding_reference", "weight": 0.30, "check_expression": "no funding/congratul in body", "description": "No fabricated funding claim"},
            {"name": "crunchbase_confidence_gate", "weight": 0.20, "check_expression": "cb_conf<0.7 => seg!=1", "description": "Gate on evidence"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.35, "metadata": make_meta("P01", 4.4 + v * 0.02),
    }


def gen_p02(v: int) -> Dict:
    """Post-layoff company classified as hypergrowth."""
    roles_new = [5, 6, 7, 8, 9, 10][v % 6]
    c = rand_company(v + 1)
    name = rand_person(v + 1)
    return {
        "task_id": next_id(), "category": "icp_misclassification", "probe_id": "P02",
        "source_mode": "programmatic", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.9, "recently_funded": True,
                                  "funding_stage": "Series C", "funding_amount_usd": 45000000,
                                  "last_funding_date": past_date(90)},
            "playwright_signal": {"open_engineering_roles": roles_new, "confidence": 0.8,
                                  "role_titles": ["Software Engineer", "Data Engineer"],
                                  "page_timestamp_days_ago": 5},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.95, "had_layoffs": True,
                               "layoff_date_days_ago": 45, "match_type": "exact"},
            "headcount_estimate": 85, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": random.choice(US_TIMEZONES),
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 3,
            "email_subject": "Request: scaling your engineering team post-Series C",
            "email_body": f"Hi {name},\n\nWith your Series C funding and {roles_new} open engineering roles, your team is clearly scaling fast. We help hypergrowth companies build engineering capacity rapidly.\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 51, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 2, "failure_detected": True,
            "failure_type": "layoff_signal_overridden_by_growth",
            "expected_behavior": "segment=2 (post_layoff). had_layoffs=True must take priority over headcount_growth. Cost-efficiency framing required.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "segment_correct", "weight": 0.40, "check_expression": "segment_assigned==2", "description": "Post-layoff must win"},
            {"name": "layoff_priority", "weight": 0.35, "check_expression": "had_layoffs and seg!=3", "description": "Layoff trumps growth"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
            {"name": "signal_grounding", "weight": 0.10, "check_expression": "layoff or restructure in body", "description": "Signal referenced"},
        ]},
        "expected_score": 0.25, "metadata": make_meta("P02", 4.5 + v * 0.01),
    }


def gen_p03(v: int) -> Dict:
    """IT staffing competitor misidentified as ICP prospect."""
    c = rand_company(v + 2)
    name = rand_person(v + 2)
    roles = 35 + v * 3
    return {
        "task_id": next_id(), "category": "icp_misclassification", "probe_id": "P03",
        "source_mode": "programmatic", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}-solutions.in", "prospect_name": f"{c} Solutions",
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": roles, "confidence": 0.8,
                                  "role_titles": ["Software Engineer", "Java Developer", "SAP Consultant", "Offshore Developer"],
                                  "page_timestamp_days_ago": 2},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 500, "ai_maturity_score": 1,
            "prospect_country": "IN", "prospect_timezone": "Asia/Kolkata",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 3,
            "email_subject": "Request: staffing your engineering team",
            "email_body": f"Hi {name},\n\nWith {roles} open engineering roles your team is expanding rapidly. We help high-growth engineering teams scale faster. Would 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 42, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": "OUTREACH_SENT",
        },
        "ground_truth": {
            "correct_segment": -1, "failure_detected": True,
            "failure_type": "competitor_not_suppressed_before_outreach",
            "expected_behavior": "IT staffing firms must be flagged as requires_human_review=True. No outreach until manual ICP confirmation.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_outreach_to_competitor", "weight": 0.50, "check_expression": "hs_lead_status not in ['OUTREACH_SENT','CONNECTED']", "description": "Staffing firms must not receive outreach"},
            {"name": "requires_human_review_flag", "weight": 0.35, "check_expression": "industry_vertical in [staffing,outsourcing]=>human_review", "description": "Flag for manual review"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.15, "metadata": make_meta("P03", 4.6),
    }


def gen_p04(v: int) -> Dict:
    """Pre-revenue startup fast-tracked as high-value."""
    c = rand_company(v + 3)
    name = rand_person(v + 3)
    return {
        "task_id": next_id(), "category": "icp_misclassification", "probe_id": "P04",
        "source_mode": "programmatic", "difficulty": "easy",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Pre-Seed", "funding_amount_usd": 500000,
                                  "last_funding_date": past_date(30 + v * 5)},
            "playwright_signal": {"open_engineering_roles": 1, "confidence": 0.8,
                                  "role_titles": ["Founding Engineer"],
                                  "page_timestamp_days_ago": 7},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 3, "ai_maturity_score": 0,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Congratulations on the pre-seed round",
            "email_body": f"Hi {name},\n\nCongratulations on closing your pre-seed round. Now is the perfect time to scale your engineering team. We help recently-funded startups like yours staff engineers fast. Would 15 minutes this week work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 46, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": "CONNECTED",
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "pre_seed_headcount_below_threshold",
            "expected_behavior": "segment=0. headcount=3 and pre-seed stage mean no fast-track. Minimum headcount=20 required for segment=1.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "segment_correct", "weight": 0.40, "check_expression": "segment_assigned==0", "description": "Pre-seed/tiny team stays generic"},
            {"name": "no_fast_track", "weight": 0.30, "check_expression": "hs_lead_status!='CONNECTED'", "description": "No CONNECTED status without qualification"},
            {"name": "no_funding_reference", "weight": 0.20, "check_expression": "no funding congratul in body", "description": "No premature congratulations"},
            {"name": "no_banned_phrases", "weight": 0.10, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.10, "metadata": make_meta("P04", 4.3),
    }


def gen_p05(v: int) -> Dict:
    """Stealth-mode AI company scored as low maturity."""
    c = rand_company(v + 4)
    name = rand_person(v + 4)
    return {
        "task_id": next_id(), "category": "icp_misclassification", "probe_id": "P05",
        "source_mode": "multi_llm_synthesis", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}.ai", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": 0, "confidence": 0.1,
                                  "role_titles": [],
                                  "page_timestamp_days_ago": None},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 0, "ai_maturity_score": 0,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 0,
            "email_subject": "Question: scaling your engineering team",
            "email_body": f"Hi {name},\n\nAs you scale your engineering team at {c}, the challenge is usually recruiting capacity versus speed. We help startups build engineering capacity. Would 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 44, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "llm_invents_profile_on_zero_signal",
            "expected_behavior": "All signals confidence=0.0 → zero-signal mode. Email must acknowledge limited public info and ask a diagnostic question. Must NOT assume scaling or team-size.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "zero_signal_acknowledged", "weight": 0.45, "check_expression": "'don't have' or 'limited' or 'public' in body", "description": "Must name signal gap"},
            {"name": "no_assumption_of_scale", "weight": 0.30, "check_expression": "'scale' and 'as you' not together", "description": "Must not assume growth trajectory"},
            {"name": "diagnostic_question", "weight": 0.15, "check_expression": "question mark in body", "description": "Must ask vs assert"},
            {"name": "no_banned_phrases", "weight": 0.10, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.45, "metadata": make_meta("P05", 4.7, "multi_llm_synthesis"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 2 — Hiring-Signal Over-Claiming  (28 tasks: P06×7, P07×7, P08×7, P09×7)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p06(v: int) -> Dict:
    """Stale job post claimed as 'aggressive hiring'."""
    c = rand_company(v + 5)
    name = rand_person(v + 5)
    stale_days = [65, 75, 90, 120, 150, 180, 240][v % 7]
    return {
        "task_id": next_id(), "category": "hiring_signal_over_claiming", "probe_id": "P06",
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": 1, "confidence": 0.8,
                                  "role_titles": ["Software Engineer"],
                                  "page_timestamp_days_ago": stale_days},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 30, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/Chicago",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 0,
            "email_subject": "Question: your engineering hiring",
            "email_body": f"Hi {name},\n\nI noticed you're actively building out the engineering team. The challenge most teams face at this stage is recruiting velocity. We help companies like yours staff engineers fast.\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 55, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "stale_role_asserted_as_active_hiring",
            "expected_behavior": f"Job post is {stale_days} days old (>60 day threshold). Email must not reference 'actively building' or 'growing team'. Use interrogative: 'I saw a software engineering role on your careers page — is the search still active?'",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "recency_gated", "weight": 0.50, "check_expression": "page_age>60=>no hiring assertion", "description": "Stale signals must use interrogative"},
            {"name": "no_active_hiring_claim", "weight": 0.30, "check_expression": "'actively building' not in body", "description": "No false hiring assertion"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P06", 4.4),
    }


def gen_p07(v: int) -> Dict:
    """Playwright follows redirect to ATS, inflates role count."""
    c = rand_company(v + 6)
    name = rand_person(v + 6)
    ats_domains = ["lever.co", "greenhouse.io", "ashbyhq.com", "workable.com", "recruitee.com", "breezy.hr", "smartrecruiters.com"]
    ats = ats_domains[v % len(ats_domains)]
    roles = [8, 10, 12, 14, 16, 18, 20][v % 7]
    return {
        "task_id": next_id(), "category": "hiring_signal_over_claiming", "probe_id": "P07",
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.8, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 22000000,
                                  "last_funding_date": past_date(60)},
            "playwright_signal": {"open_engineering_roles": roles, "confidence": 0.8,
                                  "role_titles": ["Software Engineer", "Backend Engineer"],
                                  "page_timestamp_days_ago": 3,
                                  "_redirect_domain": ats},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 55, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": f"Request: {roles} open engineering roles — can we help?",
            "email_body": f"Hi {name},\n\nI see you have {roles} open engineering roles — that's significant velocity for a team at your stage post-Series B. We help recently-funded teams like yours staff engineers rapidly.\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 52, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "ats_redirect_inflates_role_count",
            "expected_behavior": f"Playwright redirected to {ats} (known ATS). Confidence must be downgraded to 0.6 and email must hedge: 'I noticed a number of engineering roles on your careers page' rather than citing the exact inflated count.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_exact_role_count_from_ats", "weight": 0.45, "check_expression": f"'{roles} open' or '{roles} role' not in body when via ATS redirect", "description": "ATS redirect means count is uncertain"},
            {"name": "confidence_aware_phrasing", "weight": 0.35, "check_expression": "hedged language when ats redirect", "description": "Use 'a number of' not exact count"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P07", 4.3),
    }


def gen_p08(v: int) -> Dict:
    """Leadership change email sent after executive departed."""
    c = rand_company(v + 7)
    name = rand_person(v + 7)
    days_ago = [16, 20, 25, 30, 35, 40, 50][v % 7]
    return {
        "task_id": next_id(), "category": "hiring_signal_over_claiming", "probe_id": "P08",
        "source_mode": "trace_derived", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 30000000,
                                  "last_funding_date": past_date(120)},
            "playwright_signal": {"open_engineering_roles": 4, "confidence": 0.75,
                                  "role_titles": ["Backend Engineer", "Platform Engineer"],
                                  "page_timestamp_days_ago": 14},
            "pdl_signal": {"confidence": 0.85, "leadership_change": True,
                           "change_role": "VP Engineering", "days_since_change": days_ago},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 70, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Context: your new VP Engineering",
            "email_body": f"Hi {name},\n\nCongratulations on the new VP of Engineering appointment — that's exactly the moment teams decide how to scale. New engineering leaders typically reassess vendor and offshore mix in their first 90 days.\n\nWould 15 minutes be useful?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 56, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "leadership_change_stale_assertion",
            "expected_behavior": f"days_since_change={days_ago} (>15 days). Must use hedged language: 'I noticed a recent transition in engineering leadership' not 'new VP of Engineering'. The person may have already departed.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "hedged_leadership_language", "weight": 0.50, "check_expression": "'new VP' not in body when days>15", "description": "Hedge leadership reference after 15 days"},
            {"name": "no_congratulations", "weight": 0.30, "check_expression": "'congratulations' not in body for stale change", "description": "No congratulatory framing for potentially-departed exec"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P08", 4.2, "trace_derived"),
    }


def gen_p09(v: int) -> Dict:
    """Data analyst roles inflate AI maturity score."""
    c = rand_company(v + 8)
    name = rand_person(v + 8)
    bi_roles = ["Data Analyst", "BI Developer", "Tableau Developer", "Power BI Analyst",
                "Business Intelligence Engineer", "Analytics Engineer", "Reporting Analyst"][v % 7]
    return {
        "task_id": next_id(), "category": "hiring_signal_over_claiming", "probe_id": "P09",
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.8, "recently_funded": True,
                                  "funding_stage": "Series A", "funding_amount_usd": 12000000,
                                  "last_funding_date": past_date(80)},
            "playwright_signal": {"open_engineering_roles": 5, "confidence": 0.8,
                                  "role_titles": [bi_roles, "Data Analyst", "BI Developer",
                                                  "Backend Engineer", "QA Engineer"],
                                  "page_timestamp_days_ago": 8},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 40, "ai_maturity_score": 3,
            "prospect_country": "US", "prospect_timezone": "America/Chicago",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Question: your inference cost and model deployment",
            "email_body": f"Hi {name},\n\nI noticed your team is building out ML capabilities — inference cost, evaluation throughput, and model deployment velocity are the constraints that matter at your stage.\n\nWe staff ML platform engineers who have shipped production LLM systems.\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 61, "contains_banned_phrases": [], "bench_commitment": None,
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "bi_roles_inflate_ai_maturity_score",
            "expected_behavior": f"Role titles are BI/analytics ('{bi_roles}'), not ML/AI. ai_maturity_score must be <=1. Email must NOT use peer-level AI language (LLM, inference, model deployment). Use Segment 1 generic framing instead.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_ai_language_for_bi_team", "weight": 0.45, "check_expression": "'LLM' and 'inference' and 'model deployment' not in body", "description": "BI-only team must not receive ML infrastructure pitch"},
            {"name": "ai_maturity_correct", "weight": 0.35, "check_expression": "ai_maturity<=1 for BI-only roles", "description": "BI roles do not warrant ai_maturity>=2"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P09", 4.5),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 3 — Bench Over-Commitment  (28 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p11(v: int) -> Dict:
    """Agent implies 10-person ML team available in 2 weeks."""
    c = rand_company(v + 9)
    name = rand_person(v + 9)
    team_size = [8, 10, 12, 15, 20, 25, 30][v % 7]
    timeline = ["2 weeks", "2 weeks", "3 weeks", "1 month", "2 weeks", "72 hours", "1 week"][v % 7]
    return {
        "task_id": next_id(), "category": "bench_over_commitment", "probe_id": "P11",
        "source_mode": "programmatic", "difficulty": "critical",
        "input": {
            "prospect_domain": f"{c.lower()}.ai", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.95, "recently_funded": True,
                                  "funding_stage": "Series C", "funding_amount_usd": 60000000,
                                  "last_funding_date": past_date(45)},
            "playwright_signal": {"open_engineering_roles": 18, "confidence": 0.85,
                                  "role_titles": ["ML Engineer", "LLM Platform Engineer", "Staff ML Engineer"],
                                  "page_timestamp_days_ago": 4},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 90, "ai_maturity_score": 3,
            "prospect_country": "US", "prospect_timezone": "America/Los_Angeles",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 3,
            "email_subject": f"Request: staffing your ML platform team",
            "email_body": f"Hi {name},\n\nYour Series C and 18 open ML roles signal a build-out we recognise. We can help you build out a full {team_size}-person ML platform team rapidly — typically within {timeline}.\n\nOur engineers are available immediately. Would 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 62,
            "contains_banned_phrases": ["available immediately"],
            "bench_commitment": f"build out a full {team_size}-person ML platform team rapidly — typically within {timeline}",
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 3, "failure_detected": True,
            "failure_type": "bench_overcommit_without_availability_check",
            "expected_behavior": f"Bench has only 6 ML senior available. Cannot commit to {team_size} engineers in {timeline}. Replace with: 'we would scope the headcount and timeline together on a call.'",
            "banned_phrases_present": True, "bench_overcommit": True, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_headcount_commitment", "weight": 0.40, "check_expression": "no specific headcount+timeline in body", "description": "Cannot commit without bench check"},
            {"name": "bench_capacity_respected", "weight": 0.30, "check_expression": "bench_commitment is None", "description": "No over-commitment string"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
            {"name": "signal_grounding", "weight": 0.15, "check_expression": "series C or 18 roles referenced", "description": "Signal grounded"},
        ]},
        "expected_score": 0.15, "metadata": make_meta("P11", 4.6),
    }


def gen_p13(v: int) -> Dict:
    """EU prospect receives unqualified availability claims."""
    c = rand_company(v + 10)
    name = rand_person(v + 10)
    eu_country = ["DE", "NL", "FR", "SE", "FI", "DK", "AT"][v % 7]
    eu_tz = ["Europe/Berlin", "Europe/Amsterdam", "Europe/Paris", "Europe/Stockholm",
             "Europe/Helsinki", "Europe/Copenhagen", "Europe/Vienna"][v % 7]
    return {
        "task_id": next_id(), "category": "bench_over_commitment", "probe_id": "P13",
        "source_mode": "multi_llm_synthesis", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}.eu", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.9, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 35000000,
                                  "last_funding_date": past_date(50)},
            "playwright_signal": {"open_engineering_roles": 8, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer", "Platform Engineer", "Senior Engineer"],
                                  "page_timestamp_days_ago": 10},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 60, "ai_maturity_score": 2,
            "prospect_country": eu_country, "prospect_timezone": eu_tz,
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 3,
            "email_subject": "Request: scaling your engineering team rapidly",
            "email_body": f"Hi {name},\n\nYour Series B and 8 open roles suggest a team build-out. We can scale your engineering team rapidly — engineers available immediately, any stack, any timezone.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 50, "contains_banned_phrases": [], "bench_commitment": "available immediately, any timezone",
            "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "eu_unqualified_availability_claim",
            "expected_behavior": f"EU prospect (country={eu_country}). Email must acknowledge EU compliance considerations and must not claim 'available immediately' or 'any timezone'. Add region-aware qualifier.",
            "banned_phrases_present": False, "bench_overcommit": True, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_immediate_availability_eu", "weight": 0.40, "check_expression": "'available immediately' not in body for EU", "description": "EU prospects need compliance hedging"},
            {"name": "region_aware_qualifier", "weight": 0.35, "check_expression": "eu compliance or region-aware language", "description": "Must acknowledge EU context"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
            {"name": "segment_correct", "weight": 0.10, "check_expression": "segment!=3 for EU", "description": "EU -> not hypergrowth"},
        ]},
        "expected_score": 0.10, "metadata": make_meta("P13", 4.4, "multi_llm_synthesis"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 4 — Tone Drift  (32 tasks: P14×8, P15×8, P16×8, P17×8)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p14(v: int) -> Dict:
    """Email contains banned phrases that pass LLM tone-check."""
    c = rand_company(v + 11)
    name = rand_person(v + 11)
    phrase = BANNED_PHRASES_SAMPLE[v % len(BANNED_PHRASES_SAMPLE)]
    return {
        "task_id": next_id(), "category": "tone_drift", "probe_id": "P14",
        "source_mode": "trace_derived", "difficulty": "easy",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.9, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 25000000,
                                  "last_funding_date": past_date(60)},
            "playwright_signal": {"open_engineering_roles": 7, "confidence": 0.85,
                                  "role_titles": ["ML Engineer", "Backend Engineer"],
                                  "page_timestamp_days_ago": 5},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 50, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": f"Request: 15 minutes on your engineering hiring",
            "email_body": f"Hi {name},\n\nYou closed your Series B in {(date(2026,4,25)-timedelta(days=60)).strftime('%B')} and your team is hiring 7 engineers. We help teams like yours {phrase} their engineering velocity while maintaining quality.\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 55, "contains_banned_phrases": [phrase],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "banned_phrases_tone_check_false_pass",
            "expected_behavior": f"Banned phrase '{phrase}' appears in email body. LLM tone-check returned True incorrectly. Deterministic regex must catch and regenerate.",
            "banned_phrases_present": True, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_banned_phrases", "weight": 0.60, "check_expression": "banned_phrases==[]", "description": "Zero tolerance for banned phrases"},
            {"name": "word_count_ok", "weight": 0.20, "check_expression": "word_count<=120", "description": "Cold outreach word limit"},
            {"name": "signal_grounding", "weight": 0.20, "check_expression": "series B or 7 engineers in body", "description": "Signal referenced"},
        ]},
        "expected_score": 0.40, "metadata": make_meta("P14", 4.7, "trace_derived"),
    }


def gen_p15(v: int) -> Dict:
    """Email exceeds 120-word limit."""
    c = rand_company(v + 12)
    name = rand_person(v + 12)
    word_count = [125, 135, 150, 165, 180, 195, 210, 230][v % 8]
    extra_text = " ".join(["Also" if i % 5 == 0 else "additionally" for i in range(word_count - 70)])
    return {
        "task_id": next_id(), "category": "tone_drift", "probe_id": "P15",
        "source_mode": "programmatic", "difficulty": "easy",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series A", "funding_amount_usd": 15000000,
                                  "last_funding_date": past_date(45)},
            "playwright_signal": {"open_engineering_roles": 5, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer", "Data Engineer"],
                                  "page_timestamp_days_ago": 12},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 35, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Request: 15 minutes on your Series A engineering hiring",
            "email_body": f"Hi {name},\n\nYou closed your Series A in the last quarter and have 5 open engineering roles. The challenge at this stage is recruiting velocity — finding engineers quickly while maintaining technical quality. We help Series A teams staff Python, Go, data, and ML engineers managed under Tenacious project management. Our engineers have minimum three hours of synchronous overlap. We can supplement your full-time search while you continue hiring. We have placed engineers at teams similar to yours and the results have been excellent. {extra_text[:200]}\n\nWould 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": word_count, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "word_count_exceeds_120_cold_outreach",
            "expected_behavior": f"Email is {word_count} words (limit: 120 for cold outreach). LLM tone-check returned True. Deterministic word-count check must catch and trigger regeneration.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "word_count_ok", "weight": 0.70, "check_expression": "word_count<=120", "description": "Hard limit: 120 words for cold outreach"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
            {"name": "signal_grounding", "weight": 0.10, "check_expression": "series A or 5 roles in body", "description": "Signal referenced"},
        ]},
        "expected_score": 0.30, "metadata": make_meta("P15", 4.5),
    }


def gen_p16(v: int) -> Dict:
    """Reply tone escalates to pushy after 2 turns."""
    c = rand_company(v + 13)
    name = rand_person(v + 13)
    pushy = ["really think this could be transformational", "strongly recommend", "let's get something on",
             "don't miss this window", "you need to act on this", "this is urgent", "I strongly believe",
             "you really should"][v % 8]
    return {
        "task_id": next_id(), "category": "tone_drift", "probe_id": "P16",
        "source_mode": "trace_derived", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 20000000,
                                  "last_funding_date": past_date(70)},
            "playwright_signal": {"open_engineering_roles": 6, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer", "ML Engineer"],
                                  "page_timestamp_days_ago": 7},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 45, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/Chicago",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_conversation_turn": 3,
            "_prior_replies": ["interesting, tell me more", "sounds potentially relevant"],
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Re: follow-up",
            "email_body": f"Hi {name},\n\nThanks for the replies. I {pushy} for your team. Given your 6 open roles and Series B momentum, we should get this scoped before the end of the month.\n\nBook a call here: gettenacious.com/yabi\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 55, "contains_banned_phrases": [pushy],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "pushy_reply_tone_at_turn_3",
            "expected_behavior": f"Turn 3 reply contains pushy phrase '{pushy}'. Tone-check is not applied to replies in the current system. All reply turns must pass the same tone filter as initial outreach.",
            "banned_phrases_present": True, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_banned_phrases", "weight": 0.50, "check_expression": "banned_phrases==[]", "description": "Replies must also pass banned-phrase check"},
            {"name": "no_pressure_language", "weight": 0.30, "check_expression": "no urgency/pressure phrasing in reply", "description": "Non-pushy tone maintained through all turns"},
            {"name": "word_count_ok", "weight": 0.20, "check_expression": "word_count<=200 for warm reply", "description": "Warm reply limit"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P16", 4.6, "trace_derived"),
    }


def gen_p17(v: int) -> Dict:
    """Casual slang inappropriate for CTO audience."""
    c = rand_company(v + 14)
    name = rand_person(v + 14)
    slang = [("hey", "Hey"), ("awesome", "awesome"), ("vibe", "vibe well"),
             ("super excited", "super excited"), ("totally", "totally"),
             ("literally", "literally"), ("no brainer", "no-brainer"),
             ("crushing it", "crushing it")][v % 8]
    return {
        "task_id": next_id(), "category": "tone_drift", "probe_id": "P17",
        "source_mode": "multi_llm_synthesis", "difficulty": "easy",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series A", "funding_amount_usd": 10000000,
                                  "last_funding_date": past_date(90)},
            "playwright_signal": {"open_engineering_roles": 3, "confidence": 0.75,
                                  "role_titles": ["Senior Backend Engineer"],
                                  "page_timestamp_days_ago": 20},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 25, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/Los_Angeles",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_recipient_title": "CTO",
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": f"{slang[0]} — quick note about your team",
            "email_body": f"Hi {name},\n\nYour engineering team looks {slang[1]} and we think we'd {slang[1]} together. You closed a Series A in {(date(2026,4,25)-timedelta(days=90)).strftime('%B')} and have 3 open roles — {slang[1]} to step in.\n\nWould 15 minutes work?\n\nBest,\nYabi",
            "word_count": 48, "contains_banned_phrases": [slang[1]],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "casual_slang_for_cto_audience",
            "expected_behavior": f"Recipient is CTO. '{slang[1]}' is too casual for C-level executive. Subject '{slang[0]}' opener also violates the no-'Hey' rule. Tone-check must detect audience mismatch.",
            "banned_phrases_present": True, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_banned_phrases", "weight": 0.40, "check_expression": "banned_phrases==[]", "description": "Style guide"},
            {"name": "professional_subject", "weight": 0.35, "check_expression": "subject not starting with hey/quick", "description": "Professional subject for exec audience"},
            {"name": "word_count_ok", "weight": 0.15, "check_expression": "word_count<=120", "description": "Cold word limit"},
            {"name": "signal_grounding", "weight": 0.10, "check_expression": "series A or 3 roles in body", "description": "Signal referenced"},
        ]},
        "expected_score": 0.25, "metadata": make_meta("P17", 4.3, "multi_llm_synthesis"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 5 — Multi-Thread Leakage  (22 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p18(v: int) -> Dict:
    """In-memory lead state collision."""
    c1 = rand_company(v)
    c2 = rand_company(v + 15)
    return {
        "task_id": next_id(), "category": "multi_thread_leakage", "probe_id": "P18",
        "source_mode": "hand_authored", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c1.lower()}.io", "prospect_name": c1,
            "crunchbase_signal": {"confidence": 0.9, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 20000000,
                                  "last_funding_date": past_date(30)},
            "playwright_signal": {"open_engineering_roles": 5, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer"],
                                  "page_timestamp_days_ago": 7},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 40, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_concurrent_lead": {"domain": f"{c2.lower()}.com", "funding_stage": "Series A",
                                 "funding_amount_usd": 8000000},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Request: Series A engineering hiring",
            "email_body": f"Hi Alex,\n\nCongratulations on your Series A — your team at {c2} is clearly building fast with 8 open roles since the round.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 42, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "cross_lead_profile_contamination",
            "expected_behavior": f"Email for {c1} contains {c2}'s company name and funding details. In-memory _LEADS dict race condition. Each lead must maintain isolated state. Redis / per-email lock required.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "correct_company_name", "weight": 0.50, "check_expression": f"'{c2}' not in email body for {c1} lead", "description": "No cross-lead contamination"},
            {"name": "correct_funding_details", "weight": 0.35, "check_expression": "email references correct lead's funding only", "description": "Funding details must match correct lead"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.15, "metadata": make_meta("P18", 4.8, "hand_authored"),
    }


def gen_p20(v: int) -> Dict:
    """Bounced lead receives subsequent conversation replies."""
    c = rand_company(v + 16)
    return {
        "task_id": next_id(), "category": "multi_thread_leakage", "probe_id": "P20",
        "source_mode": "hand_authored", "difficulty": "critical",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": 2, "confidence": 0.7,
                                  "role_titles": ["Backend Engineer"],
                                  "page_timestamp_days_ago": 15},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 20, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/Chicago",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_lead_status": "BOUNCED",
            "_bounce_type": "hard",
        },
        "candidate_output": {
            "segment_assigned": 0,
            "email_subject": "Re: your engineering team",
            "email_body": "Hi,\n\nThanks for the reply — happy to share more about how we work. Would 15 minutes work this week?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 31, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": "OUTREACH_SENT",
        },
        "ground_truth": {
            "correct_segment": -1, "failure_detected": True,
            "failure_type": "bounce_replay_not_suppressed",
            "expected_behavior": "Lead has hard bounce. status must be 'suppressed'. No LLM call, no send attempt. Response must be {routed: false, reason: lead_suppressed}.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "bounce_suppression", "weight": 0.65, "check_expression": "no email sent to bounced lead", "description": "Hard bounce = permanent suppression"},
            {"name": "hs_status_not_outreach", "weight": 0.25, "check_expression": "hs_lead_status not OUTREACH_SENT", "description": "CRM must not show active outreach"},
            {"name": "no_banned_phrases", "weight": 0.10, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.10, "metadata": make_meta("P20", 4.9, "hand_authored"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 6 — Cost Pathology (22 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p22(v: int) -> Dict:
    """Playwright hangs on JS-heavy careers page."""
    c = rand_company(v + 17)
    return {
        "task_id": next_id(), "category": "cost_pathology", "probe_id": "P22",
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.8, "recently_funded": True,
                                  "funding_stage": "Series A", "funding_amount_usd": 14000000,
                                  "last_funding_date": past_date(60)},
            "playwright_signal": {"open_engineering_roles": 0, "confidence": 0.1,
                                  "role_titles": [],
                                  "page_timestamp_days_ago": None,
                                  "_hydration_time_seconds": 8 + v},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 30, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Request: 15 minutes on your Series A engineering hiring",
            "email_body": f"Hi Alex,\n\nYou closed your Series A recently — we help Series A teams staff engineers while the full-time search is running.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 42, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
            "_pipeline_duration_seconds": 85 + v * 5,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "playwright_timeout_causes_latency_overrun",
            "expected_behavior": f"Playwright hydration took {8+v}s (exceeded 5s timeout). Pipeline latency {85+v*5}s (target p95: 36.3s). Must set page.goto(timeout=5000) and return confidence=0.1 after timeout.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "pipeline_latency_ok", "weight": 0.50, "check_expression": "pipeline_duration_seconds<=40", "description": "Must return within p95 target"},
            {"name": "confidence_degraded_on_timeout", "weight": 0.30, "check_expression": "playwright_confidence==0.1 after timeout", "description": "Timeout => confidence=0.1"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P22", 4.2),
    }


def gen_p23(v: int) -> Dict:
    """HubSpot duplicate contact on email case mismatch."""
    c = rand_company(v + 18)
    emails = [
        ("Alice.Chen@TechStartup.io", "alice.chen@techstartup.io"),
        ("Bob.Smith@Company.COM", "bob.smith@company.com"),
        ("Carol.Jones@Startup.Co", "carol.jones@startup.co"),
        ("David.Lee@Platform.AI", "david.lee@platform.ai"),
        ("Emma.Park@Scale.IO", "emma.park@scale.io"),
        ("Frank.Wu@DataCo.Net", "frank.wu@dataco.net"),
        ("Grace.Kim@ML.AI", "grace.kim@ml.ai"),
    ]
    raw_email, norm_email = emails[v % len(emails)]
    return {
        "task_id": next_id(), "category": "cost_pathology", "probe_id": "P23",
        "source_mode": "programmatic", "difficulty": "easy",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": 3, "confidence": 0.7,
                                  "role_titles": ["Backend Engineer"],
                                  "page_timestamp_days_ago": 10},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 20, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_raw_email": raw_email,
            "_normalized_email": norm_email,
            "_prior_hs_contact_exists": True,
            "_prior_hs_contact_email": norm_email,
        },
        "candidate_output": {
            "segment_assigned": 0,
            "email_subject": "Request: 15 minutes on your engineering team",
            "email_body": "Hi,\n\nI noticed you have 3 open engineering roles. We help teams like yours staff engineers while the search is running.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 40, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None,
            "hs_lead_status": "OUTREACH_SENT",
            "_hs_contacts_created": 2,
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "hubspot_duplicate_on_email_case_mismatch",
            "expected_behavior": f"Raw email '{raw_email}' not normalized before HubSpot lookup. Creates duplicate contact alongside existing '{norm_email}'. Must normalize: email.lower().strip() before all HubSpot operations.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_hs_duplicate", "weight": 0.60, "check_expression": "hs_contacts_created==1", "description": "Exactly one HubSpot contact after operation"},
            {"name": "email_normalized", "weight": 0.25, "check_expression": "raw_email.lower()==lookup_key", "description": "Email lowercased before HubSpot lookup"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.15, "metadata": make_meta("P23", 4.1),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 7 — Dual-Control Coordination (22 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p25(v: int) -> Dict:
    """HubSpot CONNECTED without booking URL."""
    c = rand_company(v + 19)
    name = rand_person(v + 19)
    return {
        "task_id": next_id(), "category": "dual_control_coordination", "probe_id": "P25",
        "source_mode": "hand_authored", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.9, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 28000000,
                                  "last_funding_date": past_date(40)},
            "playwright_signal": {"open_engineering_roles": 8, "confidence": 0.85,
                                  "role_titles": ["ML Engineer", "Backend Engineer"],
                                  "page_timestamp_days_ago": 5},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 60, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_calcom_booking_result": {"success": False, "error": "timeout"},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Re: discovery call booked",
            "email_body": f"Hi {name},\n\nGreat — looking forward to our call. I'll send the calendar details shortly.\n\nBest,\nYabi",
            "word_count": 22, "contains_banned_phrases": [],
            "bench_commitment": None,
            "booking_slot_utc": None,
            "hs_lead_status": "CONNECTED",
            "_booking_url": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "hs_connected_without_booking_url",
            "expected_behavior": "Cal.com booking returned success=False (timeout). HubSpot must NOT be updated to CONNECTED. booking_url__c must be null. Status must remain IN_PROGRESS. The two writes must be conditional on booking success.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "hs_status_not_connected_on_fail", "weight": 0.55, "check_expression": "hs_lead_status!='CONNECTED' when booking failed", "description": "Status gated on booking success"},
            {"name": "booking_url_null_on_fail", "weight": 0.30, "check_expression": "booking_url is None when success=False", "description": "No orphaned booking state"},
            {"name": "no_banned_phrases", "weight": 0.15, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.15, "metadata": make_meta("P25", 4.7, "hand_authored"),
    }


def gen_p26(v: int) -> Dict:
    """Email sent but Langfuse trace not written."""
    c = rand_company(v + 3)
    name = rand_person(v + 3)
    return {
        "task_id": next_id(), "category": "dual_control_coordination", "probe_id": "P26",
        "source_mode": "hand_authored", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series A", "funding_amount_usd": 12000000,
                                  "last_funding_date": past_date(55)},
            "playwright_signal": {"open_engineering_roles": 4, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer"],
                                  "page_timestamp_days_ago": 8},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 30, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/Chicago",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
            "_langfuse_available": False,
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Request: 15 minutes on your Series A engineering hiring",
            "email_body": f"Hi {name},\n\nYou closed your Series A in {(date(2026,4,25)-timedelta(days=55)).strftime('%B')} and have 4 open engineering roles. We help Series A teams staff engineers fast.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 47, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None,
            "hs_lead_status": None,
            "_email_sent": True,
            "_hs_updated": False,
            "_langfuse_trace_written": False,
            "_pipeline_error": "langfuse_timeout",
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "langfuse_outage_blocks_hs_update",
            "expected_behavior": "Langfuse logging is non-blocking. langfuse_timeout must NOT propagate to halt the pipeline. Email sent + HubSpot updated regardless of Langfuse availability.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "hs_updated_despite_langfuse_failure", "weight": 0.50, "check_expression": "hs_updated==True even when langfuse_available==False", "description": "Observability must not block pipeline"},
            {"name": "email_sent_ok", "weight": 0.30, "check_expression": "email_sent==True", "description": "Email delivery not blocked"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.30, "metadata": make_meta("P26", 4.5, "hand_authored"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 8 — Scheduling Edge Cases (24 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_scheduling(probe: str, v: int, country: str, tz: str, utc_slot: str, local_hour: int) -> Dict:
    c = rand_company(v + 4)
    name = rand_person(v + 4)
    out_of_hours = local_hour < 9 or local_hour > 18
    return {
        "task_id": next_id(), "category": "scheduling_edge_cases", "probe_id": probe,
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.{'de' if country=='DE' else 'co.ke' if country=='KE' else 'com'}",
            "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 25000000,
                                  "last_funding_date": past_date(50)},
            "playwright_signal": {"open_engineering_roles": 6, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer", "Platform Engineer"],
                                  "page_timestamp_days_ago": 8},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 55, "ai_maturity_score": 2,
            "prospect_country": country, "prospect_timezone": tz,
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Request: 15 minutes on your engineering hiring",
            "email_body": f"Hi {name},\n\nYour Series B and 6 open engineering roles signal a build-out. We help Series B teams staff engineers while the full-time search continues.\n\nI've booked a 15-minute slot: [link]. Talk then!\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 50, "contains_banned_phrases": [],
            "bench_commitment": None,
            "booking_slot_utc": utc_slot,
            "hs_lead_status": "CONNECTED",
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": out_of_hours,
            "failure_type": f"booking_outside_local_hours_{country}" if out_of_hours else "ok",
            "expected_behavior": f"UTC slot {utc_slot} = {local_hour}:00 local for {tz}. {'Outside 09:00-18:00 local — must filter.' if out_of_hours else 'Within business hours.'}",
            "banned_phrases_present": False, "bench_overcommit": False,
            "booking_in_local_hours": not out_of_hours,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "booking_in_business_hours", "weight": 0.60, "check_expression": "9<=local_hour<=18", "description": f"Booking must be 09:00-18:00 {tz}"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
            {"name": "signal_grounding", "weight": 0.20, "check_expression": "series B or 6 roles in body", "description": "Signal referenced"},
        ]},
        "expected_score": 0.40 if out_of_hours else 1.0,
        "metadata": make_meta(probe, 4.3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 9 — Signal Reliability (24 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p31(v: int) -> Dict:
    """Layoffs.fyi substring match on wrong company."""
    victims = [
        ("metadataplatform.io", "MetaDataPlatform", "Meta", 10000),
        ("apple-consulting.com", "Apple Consulting", "Apple", 1200),
        ("amazontools.io", "AmazonTools", "Amazon", 9000),
        ("googleanalytics-partner.com", "GoogleAnalytics Partner", "Google", 12000),
        ("microsoft-partner.io", "MicrosoftPartner", "Microsoft", 10000),
        ("twitter-analytics.ai", "TwitterAnalytics", "Twitter", 3700),
        ("netflix-studio.com", "NetflixStudio", "Netflix", 300),
    ]
    domain, company, big_co, layoff_count = victims[v % len(victims)]
    name = rand_person(v + 5)
    return {
        "task_id": next_id(), "category": "signal_reliability", "probe_id": "P31",
        "source_mode": "programmatic", "difficulty": "hard",
        "input": {
            "prospect_domain": domain, "prospect_name": company,
            "crunchbase_signal": {"confidence": 0.0, "recently_funded": False, "funding_stage": None,
                                  "funding_amount_usd": None, "last_funding_date": None},
            "playwright_signal": {"open_engineering_roles": 3, "confidence": 0.7,
                                  "role_titles": ["Backend Engineer"],
                                  "page_timestamp_days_ago": 14},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.95, "had_layoffs": True,
                               "layoff_date_days_ago": 30,
                               "match_type": "substring",
                               "_matched_company": big_co,
                               "_layoff_count": layoff_count},
            "headcount_estimate": 25, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 2,
            "email_subject": "Context: lower-cost engineering capacity post-restructure",
            "email_body": f"Hi {name},\n\nAfter a restructure the teams that survive often need to maintain delivery output while reducing cost. We help post-layoff teams like yours staff engineers affordably.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 50, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "layoffs_fyi_substring_match_wrong_company",
            "expected_behavior": f"layoffs.fyi matched '{big_co}' substring in '{company}'. Match type=substring is insufficient. Requires exact company name match OR domain-root match. had_layoffs must be False for '{company}'. Email must not use post-layoff framing.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "no_false_layoff_signal", "weight": 0.50, "check_expression": "match_type=='exact' or 'domain' before setting had_layoffs=True", "description": "Substring match insufficient for layoff signal"},
            {"name": "segment_correct", "weight": 0.30, "check_expression": "segment_assigned==0", "description": "No post-layoff segment on false signal"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P31", 4.4),
    }


def gen_p32(v: int) -> Dict:
    """Crunchbase funding date 2 years old treated as recent."""
    c = rand_company(v + 6)
    name = rand_person(v + 6)
    months_ago = [13, 16, 19, 22, 25, 28, 32][v % 7]
    days_ago = months_ago * 30
    return {
        "task_id": next_id(), "category": "signal_reliability", "probe_id": "P32",
        "source_mode": "programmatic", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.9, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 30000000,
                                  "last_funding_date": past_date(days_ago)},
            "playwright_signal": {"open_engineering_roles": 4, "confidence": 0.75,
                                  "role_titles": ["Backend Engineer", "Data Engineer"],
                                  "page_timestamp_days_ago": 10},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 50, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {"generated_at": None, "gaps": []},
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Congratulations on the Series B funding",
            "email_body": f"Hi {name},\n\nCongratulations on closing your Series B — with {days_ago//30} months since the round your team is probably in full hiring mode. We help recently-funded teams like yours staff engineers fast.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 52, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 0, "failure_detected": True,
            "failure_type": "stale_funding_treated_as_recent",
            "expected_behavior": f"last_funding_date is {months_ago} months ago (>{6} month threshold). recently_funded must be False. Deterministic threshold: RECENTLY_FUNDED_WINDOW_DAYS=180. LLM must not determine recency.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "recency_window_enforced", "weight": 0.45, "check_expression": f"days_since_funding>{180} => recently_funded=False", "description": "Deterministic 180-day window"},
            {"name": "segment_correct", "weight": 0.30, "check_expression": "segment_assigned==0", "description": "Stale funding => generic segment"},
            {"name": "no_congratulations", "weight": 0.15, "check_expression": "no congratulations for stale funding", "description": "No stale congratulations"},
            {"name": "no_banned_phrases", "weight": 0.10, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.10, "metadata": make_meta("P32", 4.3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY 10 — Gap Over-Claiming (18 tasks)
# ══════════════════════════════════════════════════════════════════════════════

def gen_p35(v: int) -> Dict:
    """Competitor brief cites gap that competitor just filled."""
    c = rand_company(v + 7)
    name = rand_person(v + 7)
    gaps = ["lacks async interview scheduling", "no AI-native candidate matching",
            "no structured feedback loop", "lacks multilingual support",
            "no mobile app for candidates", "no API for ATS integration",
            "lacks video interviewing"][v % 7]
    days_since_generated = [65, 80, 95, 110, 130, 150, 180][v % 7]
    return {
        "task_id": next_id(), "category": "gap_over_claiming", "probe_id": "P35",
        "source_mode": "multi_llm_synthesis", "difficulty": "medium",
        "input": {
            "prospect_domain": f"{c.lower()}.io", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series B", "funding_amount_usd": 28000000,
                                  "last_funding_date": past_date(60)},
            "playwright_signal": {"open_engineering_roles": 7, "confidence": 0.8,
                                  "role_titles": ["ML Engineer", "Backend Engineer"],
                                  "page_timestamp_days_ago": 7},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 60, "ai_maturity_score": 2,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {
                "generated_at": past_date(days_since_generated),
                "gaps": [{"gap": gaps, "relevance_tags": ["scheduling", "ai"]}, {"gap": "no dedicated ML infra team", "relevance_tags": ["ml"]}],
            },
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Question: competitor gap in your space",
            "email_body": f"Hi {name},\n\nI research the tools your competitors use. One gap I've identified: Competitor X {gaps} — a disadvantage they have yet to close. Our ML engineers have shipped exactly this capability for teams like yours.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 58, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "competitor_gap_brief_stale",
            "expected_behavior": f"competitor_gap_brief.generated_at is {days_since_generated} days ago (>60 day stale threshold). Gap claims must include 'as of [date]' qualifier. Brief must be refreshed or hedged.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "temporal_qualifier_present", "weight": 0.45, "check_expression": "'as of' in body or generated_at in body", "description": "Stale gaps must be time-qualified"},
            {"name": "no_current_fact_assertion", "weight": 0.35, "check_expression": "no present-tense assertion on >60 day old gap", "description": "Cannot assert current state from stale brief"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P35", 4.2, "multi_llm_synthesis"),
    }


def gen_p36(v: int) -> Dict:
    """Competitor advantage cited is irrelevant to prospect stack."""
    c = rand_company(v + 8)
    name = rand_person(v + 8)
    irrelevant_gaps = [
        ("mobile engineering capability", ["backend_api_only"], "mobile"),
        ("iOS/Android development", ["backend_api_only"], "mobile"),
        ("embedded systems expertise", ["web_saas"], "embedded"),
        ("blockchain development", ["ml_platform"], "blockchain"),
        ("AR/VR engineering", ["data_platform"], "ar_vr"),
        ("hardware integration", ["fintech_api"], "hardware"),
        ("game engine experience", ["enterprise_saas"], "gaming"),
    ]
    gap_text, irrelevant_stacks, gap_type = irrelevant_gaps[v % len(irrelevant_gaps)]
    return {
        "task_id": next_id(), "category": "gap_over_claiming", "probe_id": "P36",
        "source_mode": "hand_authored", "difficulty": "hard",
        "input": {
            "prospect_domain": f"{c.lower()}.com", "prospect_name": c,
            "crunchbase_signal": {"confidence": 0.85, "recently_funded": True,
                                  "funding_stage": "Series A", "funding_amount_usd": 15000000,
                                  "last_funding_date": past_date(70)},
            "playwright_signal": {"open_engineering_roles": 4, "confidence": 0.8,
                                  "role_titles": ["Backend Engineer", "API Engineer", "Python Engineer"],
                                  "page_timestamp_days_ago": 10},
            "pdl_signal": {"confidence": 0.0, "leadership_change": False, "change_role": None, "days_since_change": None},
            "layoffs_signal": {"confidence": 0.0, "had_layoffs": False, "layoff_date_days_ago": None, "match_type": "none"},
            "headcount_estimate": 30, "ai_maturity_score": 1,
            "prospect_country": "US", "prospect_timezone": "America/New_York",
            "bench_available": DEFAULT_BENCH,
            "competitor_gap_brief": {
                "generated_at": past_date(20),
                "gaps": [{"gap": gap_text, "relevance_tags": [gap_type]},
                         {"gap": "no Python expertise", "relevance_tags": ["python", "backend"]}],
            },
            "_detected_stack": irrelevant_stacks,
        },
        "candidate_output": {
            "segment_assigned": 1,
            "email_subject": "Question: your engineering stack",
            "email_body": f"Hi {name},\n\nResearching your space I found a gap: Competitor X lacks {gap_text} — we can support your {gap_type} and cross-platform needs while also staffing your backend team.\n\nWould 15 minutes work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
            "word_count": 50, "contains_banned_phrases": [],
            "bench_commitment": None, "booking_slot_utc": None, "hs_lead_status": None,
        },
        "ground_truth": {
            "correct_segment": 1, "failure_detected": True,
            "failure_type": "competitor_gap_irrelevant_to_prospect_stack",
            "expected_behavior": f"Prospect stack is {irrelevant_stacks} (backend/API only). Gap '{gap_text}' is irrelevant. Only gaps matching prospect's detected role types (Python, Backend, API) should be cited. Filter gaps by relevance_tags before composing.",
            "banned_phrases_present": False, "bench_overcommit": False, "booking_in_local_hours": None,
        },
        "scoring_rubric": {"dimensions": [
            {"name": "gap_relevance_filtered", "weight": 0.50, "check_expression": "gap_type not in irrelevant_stacks", "description": "Only stack-relevant gaps cited"},
            {"name": "no_irrelevant_capability_claim", "weight": 0.30, "check_expression": f"'{gap_type}' not in email body", "description": "No irrelevant capability mention"},
            {"name": "no_banned_phrases", "weight": 0.20, "check_expression": "banned_phrases==[]", "description": "Style guide"},
        ]},
        "expected_score": 0.20, "metadata": make_meta("P36", 4.5, "hand_authored"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MASTER GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_all_tasks() -> List[Dict]:
    tasks = []

    # Category 1: ICP Misclassification — 30 tasks
    for v in range(6): tasks.append(gen_p01(v))
    for v in range(6): tasks.append(gen_p02(v))
    for v in range(6): tasks.append(gen_p03(v))
    for v in range(6): tasks.append(gen_p04(v))
    for v in range(6): tasks.append(gen_p05(v))

    # Category 2: Hiring-Signal Over-Claiming — 28 tasks
    for v in range(7): tasks.append(gen_p06(v))
    for v in range(7): tasks.append(gen_p07(v))
    for v in range(7): tasks.append(gen_p08(v))
    for v in range(7): tasks.append(gen_p09(v))

    # Category 3: Bench Over-Commitment — 28 tasks (P11×14, P13×14)
    for v in range(7): tasks.append(gen_p11(v))
    for v in range(7): tasks.append(gen_p13(v))
    # additional P11 variants for hypergrowth
    for v in range(7): tasks.append(gen_p11(v + 7))
    for v in range(7): tasks.append(gen_p13(v + 7))

    # Category 4: Tone Drift — 32 tasks (8 each)
    for v in range(8): tasks.append(gen_p14(v))
    for v in range(8): tasks.append(gen_p15(v))
    for v in range(8): tasks.append(gen_p16(v))
    for v in range(8): tasks.append(gen_p17(v))

    # Category 5: Multi-Thread Leakage — 22 tasks
    for v in range(11): tasks.append(gen_p18(v))
    for v in range(11): tasks.append(gen_p20(v))

    # Category 6: Cost Pathology — 22 tasks
    for v in range(11): tasks.append(gen_p22(v))
    for v in range(11): tasks.append(gen_p23(v))

    # Category 7: Dual-Control Coordination — 22 tasks
    for v in range(11): tasks.append(gen_p25(v))
    for v in range(11): tasks.append(gen_p26(v))

    # Category 8: Scheduling Edge Cases — 24 tasks
    eu_slots = [
        ("DE", "Europe/Berlin",      "2026-05-03T22:00:00Z", 0),   # midnight Berlin
        ("NL", "Europe/Amsterdam",   "2026-05-04T21:00:00Z", 23),  # 11pm Amsterdam
        ("FR", "Europe/Paris",       "2026-05-04T05:00:00Z", 7),   # 7am Paris
        ("SE", "Europe/Stockholm",   "2026-05-04T22:30:00Z", 0),   # midnight Stockholm
        ("FI", "Europe/Helsinki",    "2026-05-04T21:00:00Z", 0),   # midnight Helsinki
        ("DE", "Europe/Berlin",      "2026-05-04T09:00:00Z", 11),  # 11am Berlin (OK)
    ]
    ea_slots = [
        ("KE", "Africa/Nairobi",     "2026-05-04T23:00:00Z", 2),   # 2am Nairobi
        ("ET", "Africa/Addis_Ababa", "2026-05-04T22:00:00Z", 1),   # 1am Addis
        ("KE", "Africa/Nairobi",     "2026-05-04T06:00:00Z", 9),   # 9am Nairobi (OK)
        ("ET", "Africa/Addis_Ababa", "2026-05-04T07:00:00Z", 10),  # 10am Addis (OK)
        ("KE", "Africa/Nairobi",     "2026-05-04T20:00:00Z", 23),  # 11pm Nairobi
        ("ET", "Africa/Addis_Ababa", "2026-05-05T00:00:00Z", 3),   # 3am Addis
    ]
    us_slots = [
        ("US", "America/Los_Angeles","2026-05-05T13:00:00Z", 6),   # 6am PT
        ("US", "America/Los_Angeles","2026-05-05T16:00:00Z", 9),   # 9am PT (OK)
        ("US", "America/New_York",   "2026-05-05T03:00:00Z", 23),  # 11pm ET
        ("US", "America/Chicago",    "2026-05-05T02:00:00Z", 21),  # 9pm CT
        ("US", "America/Denver",     "2026-05-05T14:00:00Z", 8),   # 8am MT
        ("US", "America/New_York",   "2026-05-05T14:00:00Z", 10),  # 10am ET (OK)
        ("US", "America/Los_Angeles","2026-05-05T01:00:00Z", 18),  # 6pm PT
        ("US", "America/Chicago",    "2026-05-05T15:00:00Z", 10),  # 10am CT (OK)
        ("US", "America/Los_Angeles","2026-05-05T22:00:00Z", 15),  # 3pm PT (OK) -- was out of hours variant
        ("US", "America/New_York",   "2026-05-05T23:00:00Z", 19),  # 7pm ET
        ("US", "America/Denver",     "2026-05-05T03:00:00Z", 21),  # 9pm MT
        ("US", "America/Chicago",    "2026-05-05T04:00:00Z", 23),  # 11pm CT
    ]
    for v, (country, tz, utc, lh) in enumerate(eu_slots):
        tasks.append(gen_scheduling("P27", v, country, tz, utc, lh))
    for v, (country, tz, utc, lh) in enumerate(ea_slots):
        tasks.append(gen_scheduling("P28", v + 6, country, tz, utc, lh))
    for v, (country, tz, utc, lh) in enumerate(us_slots):
        tasks.append(gen_scheduling("P29", v + 12, country, tz, utc, lh))

    # Category 9: Signal Reliability — 24 tasks (P31×7, P32×7 + 10 more)
    for v in range(7): tasks.append(gen_p31(v))
    for v in range(7): tasks.append(gen_p32(v))
    # More P32 variants for completeness
    for v in range(10): tasks.append(gen_p32(v + 7))

    # Category 10: Gap Over-Claiming — 18 tasks
    for v in range(7): tasks.append(gen_p35(v))
    for v in range(7): tasks.append(gen_p36(v))
    for v in range(4): tasks.append(gen_p35(v + 7))

    return tasks


def stratified_split(tasks: List[Dict]) -> tuple:
    """
    Stratified split by category:
      train=50%, dev=30%, held_out=20%
    Preserves category distribution.
    """
    from collections import defaultdict
    by_cat = defaultdict(list)
    for t in tasks:
        by_cat[t["category"]].append(t)

    train, dev, held_out = [], [], []
    for cat, cat_tasks in by_cat.items():
        random.shuffle(cat_tasks)
        n = len(cat_tasks)
        n_train = int(n * 0.50)
        n_dev   = int(n * 0.30)
        train    += cat_tasks[:n_train]
        dev      += cat_tasks[n_train:n_train + n_dev]
        held_out += cat_tasks[n_train + n_dev:]

    random.shuffle(train)
    random.shuffle(dev)
    random.shuffle(held_out)
    return train, dev, held_out


def write_jsonl(tasks: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")
    print(f"  Wrote {len(tasks)} tasks → {path}")


def print_summary(train, dev, held_out):
    from collections import Counter
    all_tasks = train + dev + held_out
    cat_counts = Counter(t["category"] for t in all_tasks)
    mode_counts = Counter(t["source_mode"] for t in all_tasks)
    diff_counts = Counter(t.get("difficulty", "?") for t in all_tasks)

    print("\n=== Tenacious-Bench v0.1 Dataset Summary ===")
    print(f"  Total tasks: {len(all_tasks)}")
    print(f"  Train: {len(train)} | Dev: {len(dev)} | Held-out: {len(held_out)}")
    print("\n  By category:")
    for cat, n in sorted(cat_counts.items()):
        print(f"    {cat:<40} {n}")
    print("\n  By source mode:")
    for m, n in sorted(mode_counts.items()):
        print(f"    {m:<30} {n} ({n/len(all_tasks)*100:.1f}%)")
    print("\n  By difficulty:")
    for d, n in sorted(diff_counts.items()):
        print(f"    {d:<15} {n}")
    print()


if __name__ == "__main__":
    print("Generating Tenacious-Bench v0.1 dataset (seed=42)...")
    all_tasks = generate_all_tasks()
    train, dev, held_out = stratified_split(all_tasks)

    write_jsonl(train,    TRAIN_DIR / "tasks.jsonl")
    write_jsonl(dev,      DEV_DIR / "tasks.jsonl")
    write_jsonl(held_out, HELD_OUT_DIR / "tasks.jsonl")

    print_summary(train, dev, held_out)
    print("Done. Run: python scoring_evaluator.py --partition dev --demo")
