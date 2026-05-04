"""
generate_full_training_data.py  (seed=42)

Expands the 125 Tenacious-Bench v0.1 training tasks into SFT pairs
via template parameter sweeps. No external API calls required.

SPLIT STRATEGY (Gap 2 fix):
    Splits at the PROBE level, not the variant level.  All variants of a
    given probe_id go to either sft_train or sft_eval — never both.
    This prevents semantic leakage where the eval set contains paraphrases
    of training examples from the same probe, which causes near-zero eval
    loss via memorisation rather than generalisation.

    10% of probe_id groups (by count) → sft_eval.jsonl
    90% of probe_id groups            → sft_train.jsonl

    Legacy files preferences_train.jsonl / preferences_dev.jsonl are
    still written for backward compatibility but should NOT be used as
    the train/eval split for new training runs.

Run from repo root:
    python training_data/generate_full_training_data.py

Writes (primary — use these for training):
    training_data/sft_train.jsonl   (90% of probe groups, 10 variants each)
    training_data/sft_eval.jsonl    (10% of probe groups, 10 variants each)

Writes (legacy — kept for reference only):
    training_data/preferences_train.jsonl
    training_data/preferences_dev.jsonl
"""

import json
import random
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SEED = 42
random.seed(SEED)

REPO_ROOT = Path(__file__).parent.parent
TRAIN_TASKS = REPO_ROOT / "tenacious_bench_v0.1/train/tasks.jsonl"
DEV_TASKS   = REPO_ROOT / "tenacious_bench_v0.1/dev/tasks.jsonl"

# Primary outputs (probe-level split — use these for training)
SFT_TRAIN_OUT = REPO_ROOT / "training_data/sft_train.jsonl"
SFT_EVAL_OUT  = REPO_ROOT / "training_data/sft_eval.jsonl"

# Legacy outputs (variant-level split — backward compat only)
TRAIN_OUT = REPO_ROOT / "training_data/preferences_train.jsonl"
DEV_OUT   = REPO_ROOT / "training_data/preferences_dev.jsonl"

MIN_PAIRS_TARGET = 1000
EVAL_PROBE_FRACTION = 0.10   # hold out 10% of probe groups for eval

SYSTEM_PROMPT = """You are the brief-to-email composer for Tenacious Intelligence Corporation, a B2B engineering bench provider.

## Tenacious Style Guide v2 — Hard Rules

WORD COUNT:
- Cold outreach (first contact): ≤120 words in email body
- Warm outreach (after engagement): ≤200 words
- Re-engagement (bounced/dormant): ≤100 words

BANNED PHRASES (never use any of these):
leverage, AI-powered, disrupt, world-class, A-players, skyrocket, transformational,
don't miss out, game-changer, cutting-edge, innovative solution, seamlessly, synergy,
paradigm shift, move the needle, low-hanging fruit, circle back, reach out, touch base,
scale rapidly, scale fast, rapidly scale, available immediately, within X weeks,
best-in-class, thought leader, holistic approach, value-add, end-to-end

GROUNDING RULE:
Every email must reference at least one specific, verifiable signal from the brief:
- Exact funding amount and stage (e.g., "$28M Series B in January")
- Exact number of open roles (e.g., "9 open ML roles")
- Exact leadership change (e.g., "new VP Engineering since March")
- Exact layoff date (e.g., "restructuring in February")
Do NOT make claims not supported by the signals provided.

SEGMENT RULES:
- Segment 0 (generic): No strong signal. Use diagnostic opener about open roles.
- Segment 1 (funded): crunchbase_signal.confidence >= 0.7 AND recently_funded=True. Reference funding.
- Segment 2 (leadership): pdl_signal.confidence >= 0.7 AND leadership_change=True. Reference role change.
- Segment 3 (hypergrowth): Multiple strong signals. Be specific but do NOT commit to headcount or timelines.

BENCH COMMITMENT RULE:
NEVER state a specific team size or delivery timeline. Correct: "we'd scope headcount together on a call."
Wrong: "10 engineers in 2 weeks," "we can staff a full team immediately."

CLOSING:
Always end with a specific calendar-link ask: "Would [day] at [time] work for a 15-minute call?"
For EU prospects: offer business hours in their local timezone (not UTC).

TONE:
Confident and specific. No filler phrases. No exclamation marks. First line must be signal-grounded.
"""

# ── Pools ──────────────────────────────────────────────────────────────────────

CONTACT_NAMES = [
    "Sofia", "Marcus", "Priya", "Felix", "Yuki",
    "Daniel", "Maya", "Noah", "Elena", "Kai",
    "Leila", "James", "Aisha", "Tom", "Lin",
    "Sara", "Ben", "Chloe", "Raj", "Anna",
]

DAY_SLOTS_US = [
    "Tuesday at 10 a.m. ET",
    "Wednesday at 2 p.m. PT",
    "Thursday at 11 a.m. CT",
    "Monday at 3 p.m. ET",
    "Friday at 10 a.m. PT",
    "Tuesday at 1 p.m. ET",
    "Wednesday at 9 a.m. MT",
    "Thursday at 4 p.m. ET",
    "Monday at 11 a.m. CT",
    "Friday at 2 p.m. ET",
]

DAY_SLOTS_EU = [
    "Tuesday at 10:00 CET",
    "Wednesday at 14:00 CET",
    "Thursday at 11:00 GMT",
    "Monday at 15:00 EET",
    "Friday at 10:00 CET",
    "Tuesday at 13:00 GMT",
    "Wednesday at 11:00 CET",
    "Thursday at 15:00 GMT",
]

DAY_SLOTS_OTHER = [
    "Tuesday at 10:00 EAT",
    "Wednesday at 14:00 IST",
    "Thursday at 10:00 SGT",
    "Monday at 15:00 JST",
    "Tuesday at 11:00 AEST",
    "Wednesday at 9:00 EAT",
    "Thursday at 14:00 IST",
]

EU_COUNTRIES = {
    "DE", "FR", "GB", "NL", "SE", "FI", "DK", "NO",
    "PL", "ES", "IT", "AT", "CH", "BE", "PT", "GR",
}
ASIA_COUNTRIES = {"JP", "SG", "AU", "NZ", "IN", "CN", "KR", "ET", "KE", "NG"}

# Process failure types — routing/suppression, not email generation
PROCESS_FAILURE_TYPES = {
    "bounce_replay_not_suppressed",
    "hs_connected_without_booking_url",
    "hs_connected_without_booking",
    "crm_write_without_booking",
    "multi_thread_leakage",
    "duplicate_thread_opened",
    "dual_control_coordination",
}

# ── Email templates (subject, body) ───────────────────────────────────────────
# Placeholders: {name} {company} {N} {stage} {amount} {month} {role} {day_slot}
# Bodies are kept under 120 words for cold outreach.

TEMPLATES = {
    0: [  # Segment 0: generic — no strong signal, ground on open roles
        (
            "Quick question: {company}'s {N} open engineering roles",
            "Hi {name},\n\nI noticed {company} has {N} open engineering roles. At your headcount, that typically signals a build-out phase where hiring velocity becomes the constraint.\n\nWe staff senior and mid-level engineers while the full-time search runs in parallel. We'd scope headcount together on a call.\n\nWould {day_slot} work for a 15-minute call?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{N} open engineering roles at {company}",
            "Hi {name},\n\n{company} is posting {N} open engineering roles. When teams are hiring at that pace, supplemental staffing often shortens time-to-productivity on priority projects.\n\nWe place Python, Go, and ML engineers under Tenacious project management with a minimum three-hour synchronous overlap. We'd size the engagement on a call.\n\nWould {day_slot} work for a 15-minute call?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Engineering capacity — {company}",
            "Hi {name},\n\n{company} has {N} open engineering roles. Teams at your stage sometimes use a contract bench to extend sprint capacity while the full-time pipeline moves.\n\nWe'd scope headcount together on a discovery call, no commitment before that.\n\nWould {day_slot} work for a 15-minute call?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: {company}'s engineering team",
            "Hi {name},\n\nYou currently have {N} open engineering roles listed. We work with teams your size to fill sprint capacity while full-time recruiting continues. Our engineers carry a minimum three-hour synchronous overlap.\n\nWould {day_slot} work for a 15-minute call?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "15 minutes on {company}'s engineering hiring",
            "Hi {name},\n\nI noticed {company} has {N} engineering roles open. When a team posts that many roles simultaneously, a supplemental bench often helps close the velocity gap while permanent hiring continues.\n\nWe staff senior engineers managed under Tenacious. We'd scope the engagement together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{company}: engineering build-out question",
            "Hi {name},\n\nWith {N} open engineering roles, {company} is in a growth phase. Supplemental engineers can extend sprint capacity while the full-time search runs.\n\nWe'd discuss headcount needs on a 15-minute discovery call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: open engineering roles at {company}",
            "Hi {name},\n\n{company} has {N} engineering roles open. Teams at your size often hit a recruiting velocity wall — we help bridge that gap while permanent hiring catches up.\n\nWe'd scope headcount on a call, no commitment beforehand.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{N} engineering roles open — {company}",
            "Hi {name},\n\nI see {company} is hiring for {N} engineering roles. When a team is building this fast, the bottleneck is usually speed-to-productivity.\n\nWe place senior engineers under Tenacious project management. Scope is set together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{company}'s open engineering roles",
            "Hi {name},\n\n{company} has {N} open engineering roles. I work with teams your size on supplemental engineering capacity — a bench that runs alongside full-time hiring.\n\nWe'd scope headcount together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Engineering staffing question — {company}",
            "Hi {name},\n\nI noticed {N} open engineering roles at {company}. Teams at your stage often use supplemental staffing to fill the velocity gap while full-time recruiting runs.\n\nWe staff Python, Go, ML, and DevOps engineers. We'd size the engagement on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
    ],

    1: [  # Segment 1: funded — ground on funding stage + amount + open roles
        (
            "Re: {company}'s {stage} and engineering hiring",
            "Hi {name},\n\n{company}'s {stage} ({amount} in {month}) and {N} open engineering roles suggest a build-out phase. Teams coming off a funding round often need engineers faster than a full-time search allows.\n\nWe help {stage}-stage companies staff senior engineers while permanent hiring runs in parallel. We'd scope headcount together on a call.\n\nWould {day_slot} work for a 15-minute call?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{stage} timing and {N} open roles at {company}",
            "Hi {name},\n\nYour {stage} ({amount}) closed recently and {company} has {N} open engineering roles. Post-funding windows usually have tight delivery timelines — supplemental engineers help while full-time recruiting catches up.\n\nScope is discussed on a discovery call, no commitment before then.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Quick question following {company}'s {stage}",
            "Hi {name},\n\nI noticed {company}'s {stage} ({amount}) and {N} open engineering roles. Post-{stage} teams often need to staff quickly before the next milestone.\n\nWe'd scope headcount together on a 15-minute call, no commitment before that.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{amount} {stage} — engineering capacity at {company}",
            "Hi {name},\n\n{company}'s {amount} {stage} and {N} open engineering roles signal a build-out phase. We help funded teams staff engineers quickly while the permanent search continues. We'd scope the engagement together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: post-{stage} engineering at {company}",
            "Hi {name},\n\n{company} closed a {stage} ({amount} in {month}) and has {N} open engineering roles. That combination typically means a hard delivery deadline before the next fundraise.\n\nWe place engineers for exactly that window. We'd size the engagement together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{company}'s {stage}: engineering build-out",
            "Hi {name},\n\nYour {stage} ({amount}) and {N} open engineering roles at {company} signal a build-out phase. Post-funding teams often use a supplemental bench to maintain velocity while full-time hiring runs.\n\nWe'd scope headcount together on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Following {company}'s {stage}",
            "Hi {name},\n\n{company} closed {amount} in {stage} funding in {month}. With {N} open engineering roles, you're in a build-out phase. We help teams at this stage staff senior engineers while full-time hiring continues.\n\nWe'd discuss headcount needs on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Engineering staffing — {company}'s {stage}",
            "Hi {name},\n\n{company}'s {stage} ({amount} in {month}) combined with {N} open engineering roles is a familiar pattern: build pressure after a funding close. We help teams staff the gap while permanent hiring runs.\n\nWe'd scope together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{company}: {stage} and engineering capacity",
            "Hi {name},\n\nYour {stage} ({amount}) and {N} open roles at {company} tell me you're in a build-out window. We staff senior engineers alongside full-time recruiting. Scope is set together on a discovery call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: {company}'s {amount} {stage}",
            "Hi {name},\n\nCongratulations on the {amount} {stage}. I see {company} has {N} open engineering roles — post-{stage} teams often have a hard staffing deadline before the next milestone.\n\nWe'd scope headcount together on a call, no commitment before that.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
    ],

    2: [  # Segment 2: leadership change — ground on new role + open roles
        (
            "Re: new {role} at {company}",
            "Hi {name},\n\nA new {role} at {company} often opens a window to reset how the engineering org is staffed. You also have {N} open engineering roles — that suggests active build-out.\n\nWe'd scope headcount together on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Engineering capacity — {company}'s new {role}",
            "Hi {name},\n\nYour new {role} joined recently. Teams with a recent leadership change and {N} open engineering roles are usually in a sprint to staff before the next major milestone.\n\nWe place senior engineers with minimum three-hour synchronous overlap. Scope is set on a discovery call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Following {company}'s new {role} appointment",
            "Hi {name},\n\n{company}'s new {role} signals a shift in engineering direction. You also have {N} open engineering roles. That combination is often when teams look at supplemental staffing options.\n\nWe'd scope the engagement together on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "New {role} at {company} — engineering build-out",
            "Hi {name},\n\nA new {role} joined {company} recently. With {N} open engineering roles, the team is in a build-out phase. We help engineering orgs staff senior talent while the full-time search runs.\n\nHeadcount is scoped on a 15-minute discovery call, no commitment before that.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: {company} leadership change and engineering hiring",
            "Hi {name},\n\nYour new {role} and {N} open engineering roles at {company} suggest a build-out phase. Leadership changes often come with delivery pressure — supplemental engineers help close the velocity gap.\n\nWe'd scope headcount together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{company}: new {role} and engineering team",
            "Hi {name},\n\nYour new {role} at {company} brings new staffing priorities. With {N} open engineering roles, we might help fill the velocity gap while permanent hiring runs.\n\nWe'd discuss scope on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{role} and {N} open roles at {company}",
            "Hi {name},\n\nA new {role} joined {company} recently alongside {N} open engineering roles. That combination usually means aggressive staffing goals before the next quarter.\n\nWe staff engineers to fill that gap. Scope is set together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: {company}'s {role} hire and build-out",
            "Hi {name},\n\nYou brought on a new {role} at {company} recently. Teams making leadership changes while posting {N} engineering roles are typically in a high-pressure build phase.\n\nWe'd scope the engagement together on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
    ],

    3: [  # Segment 3: hypergrowth — ground on funding + leadership + open roles
        (
            "Re: {company}'s engineering build-out",
            "Hi {name},\n\n{company}'s {stage} ({amount} in {month}) and {N} open engineering roles signal a build-out phase. Teams with multiple active signals often need engineers faster than full-time hiring allows.\n\nWe staff Python, Go, ML, and DevOps engineers. We'd scope headcount together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{N} open roles and {stage} at {company}",
            "Hi {name},\n\nYour {stage} ({amount}) and {N} open engineering roles put {company} in a delivery-pressure window. Supplemental engineers can fill the gap while full-time recruiting continues.\n\nScope is discussed on a discovery call, no commitment before then.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Engineering capacity — {company}",
            "Hi {name},\n\n{company} closed a {stage} ({amount} in {month}) and is hiring for {N} engineering roles. Post-funding and active hiring together typically mean a hard deadline before the next milestone.\n\nWe help teams at your stage staff engineers quickly. Headcount is scoped on the discovery call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Following {company}'s {stage} and hiring signals",
            "Hi {name},\n\n{company}'s {stage} ({amount}) and {N} open engineering roles are a strong combination. That typically means delivery pressure before the next fundraise.\n\nWe staff engineers at this stage. We'd size the engagement together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{amount} {stage} and {N} roles — {company}",
            "Hi {name},\n\nYour {stage} ({amount} in {month}) and {N} open engineering roles at {company} signal a build-out phase. Post-funding teams often need to staff before the next milestone.\n\nWe'd scope headcount together on a 15-minute call.\n\nWould {day_slot} work?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{company}: multiple growth signals",
            "Hi {name},\n\n{company}'s {stage} ({amount}) and {N} open engineering roles give a clear build-out signal. We help teams at this stage staff engineers quickly, with scope set on a discovery call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "Re: {company}'s {stage} and engineering team",
            "Hi {name},\n\n{company} closed {amount} in {stage} ({month}) and has {N} open engineering roles. That's a hard build-out signal. We staff senior engineers while full-time hiring runs.\n\nScope is set together on a call.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
        (
            "{stage} and {N} open engineering roles — {company}",
            "Hi {name},\n\n{company}'s {amount} {stage} and {N} open engineering roles signal a high-priority build phase. Teams here often need engineers faster than full-time recruiting allows.\n\nWe'd scope the engagement on a call, no commitment before that.\n\nWould {day_slot} work for 15 minutes?\n\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com"
        ),
    ],
}

# ── Process failure routing responses ─────────────────────────────────────────

PROCESS_RESPONSES = {
    "bounce": [
        "Route: suppressed. No email generated. Reason: hard bounce on record for {domain}. CRM status: unchanged. No LLM call made.",
        "Routing decision: no outreach. Hard bounce detected on {domain}. Lead status must remain suppressed. No email sent.",
        "Lead status: suppressed. No email sent to {domain}. Bounce type: hard. CRM write: blocked. Status unchanged.",
        "Action: skip. {domain} has a hard bounce flag. No outreach attempt. CRM status: lead_suppressed. No LLM call.",
    ],
    "booking_fail": [
        "Routing decision: booking failed. Cal.com returned success=False. HubSpot status must NOT be updated to CONNECTED. booking_url__c remains null. Status: IN_PROGRESS.",
        "Dual-control gate: booking must succeed before CRM write. Cal.com error = no HubSpot update. Status: IN_PROGRESS. booking_url__c: null.",
        "No CRM update. Cal.com booking returned error. Status stays IN_PROGRESS until booking confirms. booking_url: null.",
        "Gate check failed. Cal.com success=False. HubSpot: no write. Status: IN_PROGRESS. Retry booking before updating CRM.",
    ],
    "dedup": [
        "Route: duplicate thread suppressed. Active thread exists for {domain}. No new outreach sent. Route to existing thread.",
        "Deduplication triggered: {domain} already has an active thread. New outreach suppressed. Existing conversation preserved.",
        "Multi-thread guard: active thread detected for {domain}. No new email generated. Route to existing thread.",
        "Duplicate check failed: {domain} thread is active. New outreach blocked. No LLM call for generation.",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def format_amount(usd: Optional[int]) -> str:
    if not usd:
        return "undisclosed"
    if usd >= 1_000_000:
        return f"${usd // 1_000_000}M"
    if usd >= 1_000:
        return f"${usd // 1_000}K"
    return f"${usd}"


def format_month(date_str: Optional[str]) -> str:
    if not date_str:
        return "recently"
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %Y")
    except Exception:
        return "recently"


def get_day_slots(country: str) -> list:
    if country in EU_COUNTRIES:
        return DAY_SLOTS_EU
    if country in ASIA_COUNTRIES:
        return DAY_SLOTS_OTHER
    return DAY_SLOTS_US


def is_process_failure(task: dict) -> bool:
    gt = task.get("ground_truth", {})
    return (
        gt.get("failure_type", "") in PROCESS_FAILURE_TYPES
        or gt.get("correct_segment", 0) == -1
    )


def get_process_response_type(failure_type: str) -> str:
    if "bounce" in failure_type:
        return "bounce"
    if any(k in failure_type for k in ("booking", "dual_control", "hs_connected", "crm_write")):
        return "booking_fail"
    return "dedup"


def build_user_brief(task: dict) -> str:
    inp = task["input"]
    lines = [f"Prospect: {inp['prospect_name']} ({inp['prospect_domain']})"]

    cb = inp.get("crunchbase_signal", {})
    if cb.get("confidence", 0) > 0:
        if cb.get("recently_funded") and cb.get("funding_stage"):
            amount = f"${cb['funding_amount_usd']:,}" if cb.get("funding_amount_usd") else "undisclosed"
            lines.append(
                f"Crunchbase: {cb['funding_stage']} ({amount}) on {cb.get('last_funding_date', 'unknown')} "
                f"[confidence={cb['confidence']:.2f}]"
            )
        else:
            lines.append(f"Crunchbase: no recent funding detected [confidence={cb['confidence']:.2f}]")
    else:
        lines.append("Crunchbase: no data [confidence=0.00]")

    pw = inp.get("playwright_signal", {})
    if pw.get("open_engineering_roles", 0) > 0:
        roles = ", ".join(pw.get("role_titles", [])[:4])
        lines.append(
            f"Hiring: {pw['open_engineering_roles']} open engineering roles — {roles} "
            f"[confidence={pw.get('confidence', 0):.2f}]"
        )
    else:
        lines.append("Hiring: no open engineering roles detected")

    pdl = inp.get("pdl_signal", {})
    if pdl.get("leadership_change") and pdl.get("confidence", 0) > 0:
        days = f" ({pdl['days_since_change']} days ago)" if pdl.get("days_since_change") else ""
        lines.append(
            f"Leadership: new {pdl.get('change_role', 'executive')}{days} "
            f"[confidence={pdl.get('confidence', 0):.2f}]"
        )
    else:
        lines.append("Leadership: no recent changes detected")

    lo = inp.get("layoffs_signal", {})
    if lo.get("had_layoffs") and lo.get("confidence", 0) > 0:
        days = f" ({lo['layoff_date_days_ago']} days ago)" if lo.get("layoff_date_days_ago") else ""
        lines.append(
            f"Layoffs: confirmed restructuring{days} "
            f"[confidence={lo.get('confidence', 0):.2f}]"
        )

    lines.append(f"Headcount estimate: {inp.get('headcount_estimate', '?')}")
    lines.append(f"AI maturity: {inp.get('ai_maturity_score', '?')}/3")
    lines.append(f"Country: {inp.get('prospect_country', '?')} | Timezone: {inp.get('prospect_timezone', '?')}")

    bench = inp.get("bench_available", {})
    if bench:
        role_names = {
            "python_senior": "Python Senior",
            "go_senior": "Go Senior",
            "ml_senior": "ML Senior",
            "data_mid": "Data Mid",
            "devops_mid": "DevOps Mid",
        }
        bench_str = " | ".join(
            f"{label}: {bench[k]}" for k, label in role_names.items() if k in bench
        )
        lines.append(f"Bench available: {bench_str}")

    gt = task.get("ground_truth", {})
    seg = gt.get("correct_segment", 0)
    lines.append(f"\nAssign segment: {seg} (0=generic, 1=funded, 2=leadership, 3=hypergrowth)")
    lines.append("Write the outreach email (subject + body). Follow all style guide rules.")
    return "\n".join(lines)


def fill_template(tmpl: str, task: dict, contact: str, day_slot: str) -> str:
    inp = task["input"]
    cb = inp.get("crunchbase_signal", {})
    pw = inp.get("playwright_signal", {})
    pdl = inp.get("pdl_signal", {})

    return tmpl.format(
        name=contact,
        company=inp.get("prospect_name", "your company"),
        N=pw.get("open_engineering_roles", "several"),
        stage=cb.get("funding_stage", "funding round"),
        amount=format_amount(cb.get("funding_amount_usd")),
        month=format_month(cb.get("last_funding_date")),
        role=pdl.get("change_role", "executive") if pdl.get("leadership_change") else "executive",
        day_slot=day_slot,
    )


def body_word_count(email: str) -> int:
    if "\n\n" in email:
        body = email.split("\n\n", 1)[1]
    else:
        body = email
    return len(body.split())


def generate_variants(task: dict, n_variants: int) -> list:
    pairs = []
    gt = task.get("ground_truth", {})
    inp = task.get("input", {})

    user_brief = build_user_brief(task)
    country = inp.get("prospect_country", "US")
    day_pool = get_day_slots(country)

    if is_process_failure(task):
        failure_type = gt.get("failure_type", "")
        resp_type = get_process_response_type(failure_type)
        responses = PROCESS_RESPONSES.get(resp_type, PROCESS_RESPONSES["dedup"])
        domain = inp.get("prospect_domain", "unknown")
        for i in range(min(n_variants, len(responses))):
            pairs.append({
                "system": SYSTEM_PROMPT,
                "prompt": user_brief,
                "chosen": responses[i].format(domain=domain),
                "task_id": task["task_id"],
                "category": task["category"],
                "source_mode": task["source_mode"],
                "difficulty": task["difficulty"],
                "probe_id": task["probe_id"],
                "quality_score": None,
                "variant_idx": i,
            })
        return pairs

    seg = gt.get("correct_segment", 0)
    tmpls = TEMPLATES.get(seg, TEMPLATES[0])

    for i in range(n_variants):
        subj_tmpl, body_tmpl = tmpls[i % len(tmpls)]
        contact = CONTACT_NAMES[i % len(CONTACT_NAMES)]
        day_slot = day_pool[i % len(day_pool)]

        try:
            subject = fill_template(subj_tmpl, task, contact, day_slot)
            body = fill_template(body_tmpl, task, contact, day_slot)
        except KeyError as e:
            log.debug("Template fill skipped for %s: %s", task["task_id"], e)
            continue

        if body_word_count(body) > 120:
            continue

        pairs.append({
            "system": SYSTEM_PROMPT,
            "prompt": user_brief,
            "chosen": f"Subject: {subject}\n\n{body}",
            "task_id": task["task_id"],
            "category": task["category"],
            "source_mode": task["source_mode"],
            "difficulty": task["difficulty"],
            "probe_id": task["probe_id"],
            "quality_score": None,
            "variant_idx": i,
        })

    return pairs


def load_tasks(path: Path) -> list:
    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def write_jsonl(pairs: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


def process_partition(tasks: list, n_email_variants: int, n_process_variants: int) -> list:
    all_pairs = []
    for task in tasks:
        n = n_process_variants if is_process_failure(task) else n_email_variants
        all_pairs.extend(generate_variants(task, n))
    return all_pairs


# ── Probe-level split (Gap 2 fix) ─────────────────────────────────────────────

def probe_level_split(tasks: list, eval_fraction: float = EVAL_PROBE_FRACTION, seed: int = SEED):
    """Split tasks by probe_id to prevent variant-level semantic leakage.

    All variants of any given probe_id end up in either the training set or
    the eval set — never in both.  This ensures the model cannot achieve low
    eval loss simply by interpolating between paraphrases of the same probe
    seen during training.

    Returns (train_tasks, eval_tasks).
    """
    probe_groups: dict = defaultdict(list)
    for task in tasks:
        probe_groups[task["probe_id"]].append(task)

    probe_ids = sorted(probe_groups.keys())
    rng = random.Random(seed)
    rng.shuffle(probe_ids)

    n_eval = max(2, round(len(probe_ids) * eval_fraction))
    eval_pids = set(probe_ids[:n_eval])
    train_pids = set(probe_ids[n_eval:])

    train_t = [t for pid in sorted(train_pids) for t in probe_groups[pid]]
    eval_t  = [t for pid in sorted(eval_pids)  for t in probe_groups[pid]]

    log.info(
        "Probe-level split: %d probe groups → %d train probes (%d tasks) / %d eval probes (%d tasks)",
        len(probe_ids),
        len(train_pids), len(train_t),
        len(eval_pids),  len(eval_t),
    )
    return train_t, eval_t


def main():
    random.seed(SEED)

    log.info("Loading training tasks: %s", TRAIN_TASKS)
    train_tasks = load_tasks(TRAIN_TASKS)
    log.info("  %d training tasks loaded", len(train_tasks))

    # ── Primary output: probe-level split ─────────────────────────────────
    sft_train_tasks, sft_eval_tasks = probe_level_split(train_tasks)

    sft_train_pairs = process_partition(sft_train_tasks, n_email_variants=10, n_process_variants=4)
    sft_eval_pairs  = process_partition(sft_eval_tasks,  n_email_variants=10, n_process_variants=4)

    # Top up training if below MIN_PAIRS_TARGET
    if len(sft_train_pairs) < MIN_PAIRS_TARGET:
        log.info("  Below %d target — running second sweep", MIN_PAIRS_TARGET)
        random.seed(SEED + 1)
        extra = process_partition(sft_train_tasks, n_email_variants=2, n_process_variants=0)
        sft_train_pairs.extend(extra)
        log.info("  After second sweep: %d training pairs", len(sft_train_pairs))

    random.seed(SEED)
    random.shuffle(sft_train_pairs)
    write_jsonl(sft_train_pairs, SFT_TRAIN_OUT)
    write_jsonl(sft_eval_pairs,  SFT_EVAL_OUT)
    log.info("  Probe-level sft_train: %d pairs → %s", len(sft_train_pairs), SFT_TRAIN_OUT)
    log.info("  Probe-level sft_eval:  %d pairs → %s", len(sft_eval_pairs),  SFT_EVAL_OUT)

    # ── Legacy output: full train partition / dev partition ────────────────
    train_pairs = process_partition(train_tasks, n_email_variants=10, n_process_variants=4)
    if len(train_pairs) < MIN_PAIRS_TARGET:
        random.seed(SEED + 1)
        extra = process_partition(train_tasks, n_email_variants=2, n_process_variants=0)
        train_pairs.extend(extra)
    random.seed(SEED)
    random.shuffle(train_pairs)
    write_jsonl(train_pairs, TRAIN_OUT)
    log.info("  Legacy preferences_train: %d pairs → %s", len(train_pairs), TRAIN_OUT)

    dev_pairs: list = []
    if DEV_TASKS.exists():
        random.seed(SEED)
        dev_tasks = load_tasks(DEV_TASKS)
        dev_pairs = process_partition(dev_tasks, n_email_variants=4, n_process_variants=2)
        write_jsonl(dev_pairs, DEV_OUT)
        log.info("  Legacy preferences_dev: %d pairs → %s", len(dev_pairs), DEV_OUT)

    # ── Summary ────────────────────────────────────────────────────────────
    cat_counts = Counter(p["category"] for p in sft_train_pairs)
    log.info("\nSFT training pairs per category (probe-level split):")
    for cat, count in sorted(cat_counts.items()):
        log.info("  %-40s: %d", cat, count)

    eval_cat_counts = Counter(p["category"] for p in sft_eval_pairs)
    log.info("\nSFT eval pairs per category (probe-level split — zero overlap with train):")
    for cat, count in sorted(eval_cat_counts.items()):
        log.info("  %-40s: %d", cat, count)

    log.info("\nTotal sft_train pairs : %d", len(sft_train_pairs))
    log.info("Total sft_eval pairs  : %d", len(sft_eval_pairs))
    log.info("Done. Next: python training/train.py")


if __name__ == "__main__":
    main()
