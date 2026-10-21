#!/usr/bin/env python3
"""Rewrite baseline files to the values measured in valgrind reports.

The sign-off half of the regression gate: once a reviewer accepts a
regression or an improvement, CI runs this over the reports of the run they
looked at and commits the result, so nobody has to copy numbers by hand.

Only metrics that failed against their baseline move. A metric over its
absolute limit is left alone, since raising the baseline does not fix it.

Run with Bazel:
    bazel run //tools/valgrind/report:update_baselines -- \\
        --workspace /abs/path/to/checkout \\
        /abs/path/a/valgrind-callgrind.report.json
"""

import argparse
import json
import sys
from pathlib import Path

from tools.valgrind.report.metrics import (
    STATUS_OVER_LIMIT,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Report,
    baseline_literal,
    read_report,
)

SIGNED_OFF_STATUSES = (STATUS_REGRESSION, STATUS_STALE_BASELINE)


class _Number(str):
    """A json number kept as written, so untouched entries keep their format."""


def _read_flat_baseline(path: Path) -> dict[str, str]:
    """Read a baseline file as key to number literal, in file order."""
    with path.open() as f:
        baselines = json.load(f, parse_int=_Number, parse_float=_Number)
    if not isinstance(baselines, dict):
        raise ValueError("not a json object")
    for key, value in baselines.items():
        if not isinstance(value, _Number):
            raise ValueError(f"{key!r} is not a number")
    return baselines


def _write_flat_baseline(path: Path, baselines: dict[str, str]) -> None:
    lines = [f"  {json.dumps(key)}: {value}" for key, value in baselines.items()]
    path.write_text("{\n" + ",\n".join(lines) + "\n}\n")


def _resolve_baseline(workspace: Path, baseline_file: str) -> Path:
    """Map a report's baseline path into the workspace, refusing any escape.

    Reports come from CI artifacts, so the path is not trusted.
    """
    relative = Path(baseline_file)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".json":
        raise ValueError(f"{baseline_file!r} is not a workspace-relative json file")
    path = (workspace / relative).resolve()
    if not path.is_relative_to(workspace.resolve()) or not path.is_file():
        raise ValueError(f"{baseline_file!r} is not a file in the workspace")
    return path


def plan_updates(
    reports: list[Report], workspace: Path
) -> tuple[dict[Path, dict[str, str]], list[str]]:
    """Work out the new literal of every signed-off metric, grouped by file.

    Returns the updates and a note for each metric deliberately left alone.

    Raises:
        ValueError: on an unusable baseline path, or two reports sharing a
            baseline file but disagreeing on a value.
    """
    updates: dict[Path, dict[str, str]] = {}
    skipped = []
    for report in reports:
        for metric in report["metrics"]:
            if metric["status"] == STATUS_OVER_LIMIT:
                skipped.append(f"{report['label']}: {metric['key']} is over its limit")
            if metric["status"] not in SIGNED_OFF_STATUSES:
                continue

            path = _resolve_baseline(workspace, report["baseline_file"])
            literal = baseline_literal(metric)
            planned = updates.setdefault(path, {})
            if planned.get(metric["key"], literal) != literal:
                raise ValueError(
                    f"{report['baseline_file']}: reports disagree on {metric['key']!r}"
                    f" ({planned[metric['key']]} vs {literal})"
                )
            planned[metric["key"]] = literal
    return updates, skipped


def apply_updates(updates: dict[Path, dict[str, str]], workspace: Path) -> list[str]:
    """Write the planned values, returning one line per change for the log.

    Every file is read and checked before any is written, so a bad one leaves
    no half-applied sign-off behind.
    """
    files = {path: _read_flat_baseline(path) for path in sorted(updates)}
    changes = []
    for path, baselines in files.items():
        for key, literal in updates[path].items():
            if key not in baselines:
                raise ValueError(f"{path}: no {key!r} entry")
            changes.append(
                f"{path.relative_to(workspace.resolve())}: {key} "
                f"{baselines[key]} -> {literal}"
            )
            baselines[key] = literal

    for path, baselines in files.items():
        _write_flat_baseline(path, baselines)
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "reports", nargs="+", type=Path, help="Paths to valgrind report json files"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Checkout the reports' baseline paths are relative to",
    )
    args = parser.parse_args(argv)

    try:
        reports = [read_report(path) for path in args.reports]
        updates, skipped = plan_updates(reports, args.workspace)
        changes = apply_updates(updates, args.workspace)
    except (OSError, ValueError) as err:
        print(f"Error: could not update the baselines: {err}", file=sys.stderr)
        return 1

    for line in changes or ["No baseline needed updating."]:
        print(line)
    for line in skipped:
        print(f"Not updated: {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
