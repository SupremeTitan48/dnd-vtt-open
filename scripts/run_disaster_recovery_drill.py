#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from app.disaster_recovery import run_backup_restore_drill
from api.http_api import session_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Run backup/restore disaster-recovery drill for a session.")
    parser.add_argument("session_id", help="Session id to validate")
    parser.add_argument("--token-id", default="hero", help="Token id used for mutation check")
    parser.add_argument("--baseline-x", type=int, default=2, help="Baseline X position before backup")
    parser.add_argument("--baseline-y", type=int, default=2, help="Baseline Y position before backup")
    parser.add_argument("--changed-x", type=int, default=7, help="Mutation X position after backup")
    parser.add_argument("--changed-y", type=int, default=7, help="Mutation Y position after backup")
    args = parser.parse_args()

    report = run_backup_restore_drill(
        session_service,
        session_id=args.session_id,
        token_id=args.token_id,
        baseline_position=(args.baseline_x, args.baseline_y),
        changed_position=(args.changed_x, args.changed_y),
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
