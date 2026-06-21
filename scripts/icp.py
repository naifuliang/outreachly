"""ICP (Ideal Customer Profile) validation & persistence.

Generation is done by Claude (it writes ICP JSON conforming to reference/icp_schema.json).
This script does the deterministic parts: validate with field-level errors, and load/save the
active ICP to data/icp.json so discovery and the UI can use it.

CLI:
  python scripts/icp.py template            # print a blank ICP skeleton
  python scripts/icp.py validate --file F   # validate a file (or stdin); exit 1 if invalid
  python scripts/icp.py save --file F       # validate then save as the active ICP
  python scripts/icp.py show                # print the active ICP
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path

from _common import REPO_ROOT, load_env

SCHEMA_PATH = REPO_ROOT / "reference" / "icp_schema.json"
DEFAULT_ICP_PATH = REPO_ROOT / "data" / "icp.json"


def icp_path() -> Path:
    """Active-ICP file path. Override with OUTREACHLY_ICP (lets temp/test runs isolate it)."""
    load_env()
    return Path(os.environ.get("OUTREACHLY_ICP") or DEFAULT_ICP_PATH)

TEMPLATE = {
    "product": "",
    "industries": [],
    "company_size": "any",
    "geographies": [],
    "titles": [],
    "pain_points": [],
    "buying_signals": [],
    "keywords": [],
    "channels": ["email"],
    "language": "en",
}


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(icp: dict) -> list[str]:
    """Return a list of human-readable, field-scoped errors ([] means valid)."""
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(load_schema())
    errors = []
    for err in sorted(validator.iter_errors(icp), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return errors


def save_icp(icp: dict, path: Path | None = None) -> list[str]:
    """Validate then persist. Returns errors; saves only if valid."""
    errors = validate(icp)
    if errors:
        return errors
    target = Path(path) if path else icp_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(icp, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


def load_icp(path: Path | None = None) -> dict | None:
    path = Path(path) if path else icp_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_input(file: str | None) -> dict:
    raw = Path(file).read_text(encoding="utf-8") if file else sys.stdin.read()
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Outreachly ICP validate/persist.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("template", help="Print a blank ICP skeleton.")
    p_v = sub.add_parser("validate", help="Validate an ICP (file or stdin).")
    p_v.add_argument("--file")
    p_s = sub.add_parser("save", help="Validate and save the active ICP.")
    p_s.add_argument("--file")
    sub.add_parser("show", help="Print the active ICP.")
    args = parser.parse_args()

    if args.cmd == "template":
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "validate":
        try:
            icp = _read_input(args.file)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"FAIL: cannot read ICP — {exc}")
            return 1
        errors = validate(icp)
        if errors:
            print("INVALID ICP:")
            for e in errors:
                print(f"  - {e}")
            return 1
        print("VALID ICP.")
        return 0
    if args.cmd == "save":
        try:
            icp = _read_input(args.file)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"FAIL: cannot read ICP — {exc}")
            return 1
        errors = save_icp(icp)
        if errors:
            print("NOT SAVED — invalid ICP:")
            for e in errors:
                print(f"  - {e}")
            return 1
        print(f"Saved active ICP → {icp_path()}")
        return 0
    if args.cmd == "show":
        icp = load_icp()
        if icp is None:
            print("No active ICP yet.")
            return 1
        print(json.dumps(icp, ensure_ascii=False, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
