"""Shared helper for not-yet-implemented script stubs.

Keeps every stub CLI-invokable so the Skill orchestration and `--help` work from P0, while
clearly signalling which roadmap phase will implement it.
"""

from __future__ import annotations

import argparse


def stub_main(name: str, phase: str, summary: str) -> int:
    parser = argparse.ArgumentParser(prog=f"app.scripts.{name}", description=summary)
    parser.add_argument("--json", action="store_true", help="(reserved) machine-readable output")
    parser.parse_args()
    print(f"{name}: not yet implemented — scheduled for {phase}.")
    print(f"  purpose: {summary}")
    return 0
