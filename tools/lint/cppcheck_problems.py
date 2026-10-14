#!/usr/bin/env python3
"""
Print a cppcheck XML report as one line per finding, for editor problem matchers.

Each finding becomes `file:line:column: [id] severity: message`, the format the
generated VS Code "Run Cppcheck" tasks match. Findings without a location are
skipped since an editor has nowhere to show them.

Typically run on the report the lint driver merges:
    bazel run @rules_swiftnav//tools/lint:cppcheck_problems -- cppcheck-output/merged-report.xml
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Mapping, Optional, Sequence


def format_problems(report: str) -> list[str]:
    """Format the findings of a cppcheck XML report.

    Args:
        report: The report's XML content.

    Returns:
        One line per finding, at the finding's first location.
    """
    problems = []
    for error in ET.fromstring(report).iter("error"):
        location = error.find("location")
        if location is None:
            continue
        problems.append(
            f"{location.get('file')}:{location.get('line')}:{location.get('column', '0')}: "
            f"[{error.get('id')}] {error.get('severity')}: {error.get('msg')}"
        )
    return problems


def main(argv: Sequence[str], environ: Optional[Mapping[str, str]] = None) -> int:
    """Print the problems of the report named by the only argument.

    Args:
        argv: Command line arguments, without the program name.
        environ: Environment, os.environ if None.

    Returns:
        The exit code.
    """
    if environ is None:
        environ = os.environ
    if len(argv) != 1:
        print("Usage: cppcheck_problems <report.xml>", file=sys.stderr)
        return 1
    # bazel run starts the binary from its runfiles, not from where it was run.
    report = Path(environ.get("BUILD_WORKING_DIRECTORY", ".")) / argv[0]
    try:
        content = report.read_text()
    except OSError as e:
        print(f"Error: cannot read {report}: {e}", file=sys.stderr)
        return 1
    for problem in format_problems(content):
        print(problem)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
