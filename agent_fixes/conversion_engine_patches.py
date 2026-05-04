"""
conversion_engine_patches.py

Documented fixes for the two architectural bugs in the Tenacious Conversion Engine
that cannot be addressed by SFT of the email composer.

Bug 1 — Segment waterfall ordering (ICP Misclassification, Gap 3)
    Root cause: _classify_segment checks headcount_growth_pct >= 40 before
    checking had_layoffs, so a post-layoff company that subsequently posts
    many new roles always receives segment=3 (hypergrowth) instead of
    segment=2 (post_layoff).  Probe P02 documents a 31% false-positive rate.
    Fix: reorder the condition checks — had_layoffs takes priority.

Bug 2 — Non-thread-safe _LEADS store (Multi-Thread Leakage, Gap 3)
    Root cause: The in-memory dict used to cache lead state during concurrent
    email generation is not protected by a lock.  When two requests for the
    same company domain arrive simultaneously, one request's data can be
    partially overwritten by the other before the email is generated, causing
    cross-lead data contamination (wrong prospect name, wrong signals).
    Fix: wrap _LEADS access in a threading.Lock (or use a Redis-backed store
    for multi-process deployments).

Both fixes are shown as before/after code blocks so they can be applied
directly to the Tenacious Conversion Engine repository.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# BUG 1 — Segment waterfall ordering
# ═══════════════════════════════════════════════════════════════════════════════

# ── BEFORE (buggy) ────────────────────────────────────────────────────────────
#
# def _classify_segment(signals: dict) -> int:
#     """Classify a prospect into one of four segments."""
#     cb  = signals.get("crunchbase_signal", {})
#     pw  = signals.get("playwright_signal", {})
#     pdl = signals.get("pdl_signal", {})
#     lo  = signals.get("layoffs_signal", {})
#
#     recently_funded = cb.get("recently_funded", False) and cb.get("confidence", 0) >= 0.7
#     leadership_change = pdl.get("leadership_change", False) and pdl.get("confidence", 0) >= 0.7
#     headcount_growth_pct = signals.get("headcount_growth_pct", 0)
#     had_layoffs = lo.get("had_layoffs", False) and lo.get("confidence", 0) >= 0.7
#
#     # BUG: hypergrowth check fires before post-layoff check.
#     # A company that laid off staff 45 days ago but has since posted 8 new
#     # roles will have headcount_growth_pct >= 40, triggering segment=3
#     # even though had_layoffs=True should force segment=2.
#     if recently_funded and headcount_growth_pct >= 40:
#         return 3  # hypergrowth
#     if recently_funded:
#         return 1  # funded
#     if leadership_change:
#         return 2  # leadership
#     if had_layoffs:
#         return 2  # post_layoff
#     return 0      # generic


# ── AFTER (fixed) ─────────────────────────────────────────────────────────────

def _classify_segment(signals: dict) -> int:
    """Classify a prospect into one of four segments.

    Priority order (highest to lowest):
      1. post_layoff  — had_layoffs overrides all growth signals
      2. hypergrowth  — multiple strong signals: funded + high growth
      3. funded       — recent funding round confirmed by Crunchbase
      4. leadership   — recent executive hire confirmed by PDL
      5. generic      — no strong signal
    """
    cb  = signals.get("crunchbase_signal", {})
    pw  = signals.get("playwright_signal", {})   # noqa: F841 (used implicitly via signals)
    pdl = signals.get("pdl_signal", {})
    lo  = signals.get("layoffs_signal", {})

    recently_funded      = cb.get("recently_funded", False)  and cb.get("confidence", 0) >= 0.7
    leadership_change    = pdl.get("leadership_change", False) and pdl.get("confidence", 0) >= 0.7
    headcount_growth_pct = signals.get("headcount_growth_pct", 0)
    had_layoffs          = lo.get("had_layoffs", False) and lo.get("confidence", 0) >= 0.7

    # FIX: check had_layoffs FIRST — a restructuring signal overrides growth signals.
    # Probe P02: post-layoff company with subsequent hiring surge must be segment=2,
    # not segment=3.  "Scaling fast" framing is tone-deaf to a company that just cut staff.
    if had_layoffs:
        return 2  # post_layoff — takes priority over everything

    if recently_funded and headcount_growth_pct >= 40:
        return 3  # hypergrowth

    if recently_funded:
        return 1  # funded

    if leadership_change:
        return 2  # leadership

    return 0  # generic


# ── Verification test ─────────────────────────────────────────────────────────

def _test_segment_waterfall():
    """Quick smoke test for the fixed waterfall. Run: python agent_fixes/conversion_engine_patches.py"""

    # P02: post-layoff with high growth — must be segment=2, not segment=3
    signals_p02 = {
        "crunchbase_signal": {"recently_funded": True, "confidence": 0.9},
        "pdl_signal": {"leadership_change": False, "confidence": 0.0},
        "layoffs_signal": {"had_layoffs": True, "confidence": 0.95},
        "headcount_growth_pct": 45,
    }
    result = _classify_segment(signals_p02)
    assert result == 2, f"P02 regression: expected 2 (post_layoff), got {result}"
    print("P02 ✓  post-layoff + high growth → segment=2 (post_layoff)")

    # P01: bootstrapped company, no CB data — must be segment=0
    signals_p01 = {
        "crunchbase_signal": {"recently_funded": False, "confidence": 0.0},
        "pdl_signal": {"leadership_change": False, "confidence": 0.0},
        "layoffs_signal": {"had_layoffs": False, "confidence": 0.0},
        "headcount_growth_pct": 0,
    }
    result = _classify_segment(signals_p01)
    assert result == 0, f"P01 regression: expected 0 (generic), got {result}"
    print("P01 ✓  no signals → segment=0 (generic)")

    # Funded + high growth, no layoffs — should be segment=3
    signals_hypergrowth = {
        "crunchbase_signal": {"recently_funded": True, "confidence": 0.85},
        "pdl_signal": {"leadership_change": False, "confidence": 0.0},
        "layoffs_signal": {"had_layoffs": False, "confidence": 0.0},
        "headcount_growth_pct": 50,
    }
    result = _classify_segment(signals_hypergrowth)
    assert result == 3, f"Hypergrowth regression: expected 3, got {result}"
    print("Hypergrowth ✓  funded + high growth, no layoffs → segment=3 (hypergrowth)")

    print("\nAll segment waterfall tests passed.")


# ═══════════════════════════════════════════════════════════════════════════════
# BUG 2 — Non-thread-safe _LEADS store
# ═══════════════════════════════════════════════════════════════════════════════

# ── BEFORE (buggy) ────────────────────────────────────────────────────────────
#
# _LEADS: dict = {}   # shared across all threads — NOT thread-safe
#
# async def enrich_lead(domain: str, signals: dict) -> None:
#     _LEADS[domain] = signals          # race condition here
#
# async def generate_email_for_lead(domain: str) -> str:
#     signals = _LEADS[domain]          # may read partial state written by another thread
#     return _compose_email(signals)


# ── AFTER (fixed) ─────────────────────────────────────────────────────────────

import threading

_LEADS_LOCK: threading.Lock = threading.Lock()
_LEADS: dict = {}


def enrich_lead(domain: str, signals: dict) -> None:
    """Write lead signals. Thread-safe: acquires lock before mutating shared state."""
    with _LEADS_LOCK:
        _LEADS[domain] = signals


def get_lead(domain: str) -> dict:
    """Read lead signals. Thread-safe: acquires lock to prevent partial reads."""
    with _LEADS_LOCK:
        return dict(_LEADS.get(domain, {}))  # return a copy, not a reference


def clear_lead(domain: str) -> None:
    """Remove a lead from the store after processing. Prevents stale state."""
    with _LEADS_LOCK:
        _LEADS.pop(domain, None)


# ── Usage note ────────────────────────────────────────────────────────────────
#
# For multi-process deployments (e.g., multiple Gunicorn workers), threading.Lock
# is not sufficient because each process has its own memory space.  Replace the
# in-memory dict with a Redis-backed store:
#
#   import redis
#   import json
#
#   _redis = redis.Redis(host="localhost", port=6379, db=0)
#   LEAD_TTL_SECONDS = 3600  # expire after 1 hour
#
#   def enrich_lead(domain: str, signals: dict) -> None:
#       _redis.setex(f"lead:{domain}", LEAD_TTL_SECONDS, json.dumps(signals))
#
#   def get_lead(domain: str) -> dict:
#       raw = _redis.get(f"lead:{domain}")
#       return json.loads(raw) if raw else {}
#
#   def clear_lead(domain: str) -> None:
#       _redis.delete(f"lead:{domain}")


# ── Concurrency smoke test ────────────────────────────────────────────────────

def _test_thread_safe_leads():
    """Verify that concurrent writes do not produce cross-lead contamination."""
    import concurrent.futures

    domains = [f"company-{i}.com" for i in range(50)]
    signals = [{"name": d, "segment": i % 4} for i, d in enumerate(domains)]

    # Write all leads concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(lambda ds: enrich_lead(ds[0], ds[1]), zip(domains, signals)))

    # Read back and verify no cross-contamination
    errors = []
    for domain, expected in zip(domains, signals):
        got = get_lead(domain)
        if got.get("name") != expected["name"]:
            errors.append(f"{domain}: expected name={expected['name']}, got {got.get('name')}")

    if errors:
        print(f"FAILED — {len(errors)} cross-contamination errors:")
        for e in errors[:5]:
            print(f"  {e}")
    else:
        print(f"Thread-safe LEADS ✓  {len(domains)} concurrent writes, zero cross-contamination")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Bug 1: Segment waterfall ===")
    _test_segment_waterfall()
    print()
    print("=== Bug 2: Thread-safe _LEADS store ===")
    _test_thread_safe_leads()
