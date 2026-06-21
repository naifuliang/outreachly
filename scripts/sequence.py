"""Follow-up cadence scheduler — finds leads due for their next sequence step.

A lead's sequence runs: step 0 (first touch) → step 1 → … up to MAX_STEPS-1, one touch every
GAP_DAYS, and STOPS automatically once they reply (status leaves 'contacted'). This script does
the timing only — it surfaces who is due and which step. Claude writes the personalized follow-up
and sends it (`send_email`/`linkedin.dm`/`twitter.dm` with `--step <n>`), which records the step
so the next run advances.

CLI:
  python scripts/sequence.py cadence              # show the configured cadence
  python scripts/sequence.py due [--gap 3] [--max 3]   # leads due for a follow-up now
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from _common import load_env


def _utcnow() -> datetime:
    """Naive UTC now, matching sqlite's datetime('now') string format."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

DEFAULT_GAP_DAYS = 3
DEFAULT_MAX_STEPS = 3  # step 0 + two follow-ups


def _cfg(gap_days: int | None, max_steps: int | None) -> tuple[int, int]:
    load_env()
    gap = gap_days if gap_days is not None else int(os.environ.get("SEQUENCE_GAP_DAYS", DEFAULT_GAP_DAYS))
    mx = max_steps if max_steps is not None else int(os.environ.get("SEQUENCE_MAX_STEPS", DEFAULT_MAX_STEPS))
    return gap, mx


def _parse_ts(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def due_followups(now: datetime | None = None, gap_days: int | None = None,
                  max_steps: int | None = None, path: str | None = None) -> list[dict]:
    """Return leads whose next follow-up is due: status 'contacted', sequence not exhausted,
    and the last outbound touch older than GAP_DAYS. Sorted by most overdue first.
    """
    import crm

    crm.init_db(path)  # tolerate a not-yet-initialized DB
    gap, mx = _cfg(gap_days, max_steps)
    ref = now or _utcnow()  # sqlite datetime('now') is UTC
    out = []
    for lead in crm.list_leads(status="contacted", path=path):
        last = crm.last_outbound(lead["id"], path, sent_only=True)  # drafts don't drive cadence
        if not last:
            continue
        next_step = (last["sequence_step"] or 0) + 1
        if next_step > mx - 1:
            continue  # sequence exhausted
        sent = _parse_ts(last["sent_at"]) or _parse_ts(last["created_at"])
        if not sent:
            continue
        days = (ref - sent).total_seconds() / 86400.0
        if days >= gap:
            out.append({
                "lead_id": lead["id"], "name": lead["name"], "channel": last["channel"],
                "next_step": next_step, "days_since": round(days, 1),
            })
    out.sort(key=lambda r: r["days_since"], reverse=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cadence", help="Show the configured cadence.")
    p = sub.add_parser("due", help="List leads due for a follow-up now.")
    p.add_argument("--gap", type=int, default=None, help="Days between touches.")
    p.add_argument("--max", type=int, default=None, dest="max", help="Max steps (incl. first touch).")
    args = parser.parse_args()

    if args.cmd == "cadence":
        gap, mx = _cfg(None, None)
        print(f"cadence: {mx} touches max, one every {gap} day(s); stops automatically on reply.")
        return 0

    rows = due_followups(gap_days=args.gap, max_steps=args.max)
    gap, mx = _cfg(args.gap, args.max)
    if not rows:
        print(f"No follow-ups due (gap {gap}d, max {mx} steps).")
        return 0
    print(f"{len(rows)} follow-up(s) due:")
    for r in rows:
        print(f"  lead #{r['lead_id']:<4} {r['name'] or '?':<28} → step {r['next_step']} "
              f"via {r['channel']} ({r['days_since']}d since last)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
