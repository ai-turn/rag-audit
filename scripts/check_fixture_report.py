"""Check a rag-audit report against fixture expectations.

Usage:
  python scripts/check_fixture_report.py examples/flawed_rag.expectations.json report.md
  python scripts/check_fixture_report.py examples/flawed_rag.expectations.json -
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


RULE_ID = re.compile(r"(?:^### \[[A-Z]+\]\s+|^- \[[A-Z]+\]\s+)(RAG-[A-Z]\d{3})", re.M)


def findings_section(report: str) -> str:
    match = re.search(r"^## Findings\s*$", report, re.M)
    if not match:
        return report
    rest = report[match.end() :]
    next_section = re.search(r"^##\s+", rest, re.M)
    return rest[: next_section.start()] if next_section else rest


def finding_ids(report: str) -> set[str]:
    return set(RULE_ID.findall(findings_section(report)))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_report(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("expectations", type=Path)
    parser.add_argument("report", help="report markdown path, or '-' for stdin")
    args = parser.parse_args()

    expectations = load_json(args.expectations)
    found = finding_ids(read_report(args.report))

    missing = sorted(set(expectations.get("must_find", [])) - found)
    unexpected = sorted(set(expectations.get("must_not_find", [])) & found)

    if missing or unexpected:
        if missing:
            print("missing expected findings: " + ", ".join(missing), file=sys.stderr)
        if unexpected:
            print("unexpected findings: " + ", ".join(unexpected), file=sys.stderr)
        return 1

    print(f"ok: {expectations.get('target', args.report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
