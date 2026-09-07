#!/usr/bin/env python3
"""
Merge the per-target cppcheck XML reports of a Bazel build into one file.

The cppcheck aspect writes one raw machine report per linted target. The
compliance-report, htmlreport and HIS tools downstream expect a single
consolidated XML, which this script produces from the report files listed in a
Bazel Build Event Protocol JSON file.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Sequence

from tools.lint.bep import files_from_bep

# rules_lint's OUTFILE_FORMAT is "{label}.{mnemonic}.{suffix}"; the cppcheck
# aspect's mnemonic is AspectRulesLintCppCheck and its XML suffix is "xml".
# Matching on the full suffix (not just ".xml") avoids picking up unrelated
# XML outputs listed in the same BEP file.
CPPCHECK_XML_SUFFIX = ".AspectRulesLintCppCheck.xml"


def parse_xml_report(file_path: Path) -> ET.Element | None:
    """
    Parse a cppcheck XML report and return its root element.

    Args:
        file_path: Path to a cppcheck XML report

    Returns:
        The report's root element, or None if it holds no parsable XML
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # cppcheck interleaves progress lines ("Checking foo.cc ...") with the
        # report, so the document does not necessarily start at byte zero.
        xml_start = content.find("<?xml")
        if xml_start == -1:
            print(f"Warning: No XML content found in {file_path}", file=sys.stderr)
            return None

        return ET.fromstring(content[xml_start:])
    except ET.ParseError as e:
        print(f"Warning: Failed to parse XML in {file_path}: {e}", file=sys.stderr)
        return None
    except OSError as e:
        print(f"Warning: Error reading {file_path}: {e}", file=sys.stderr)
        return None


def _extract_error_location(error: ET.Element) -> tuple[str, str, str]:
    """
    Extract location information from an error element.

    Args:
        error: An XML error element

    Returns:
        Tuple of (file_path, line_num, col_num) as strings
    """
    location = error.find("location")
    if location is not None:
        return (
            location.get("file", ""),
            location.get("line", ""),
            location.get("column", ""),
        )
    return ("", "", "")


def _create_error_key(error: ET.Element) -> tuple[str, str, str, str, str]:
    """
    Create a unique key for error deduplication.

    Args:
        error: An XML error element

    Returns:
        Tuple of (error_id, file_path, line_num, col_num, error_msg)
    """
    file_path, line_num, col_num = _extract_error_location(error)
    return (
        error.get("id", ""),
        file_path,
        line_num,
        col_num,
        error.get("msg", ""),
    )


def _merge_errors(
    errors_elem: ET.Element | None,
    merged_errors: ET.Element,
    seen_errors: set,
) -> None:
    """
    Merge error elements with deduplication.

    Args:
        errors_elem: Source errors XML element
        merged_errors: Target merged errors XML element
        seen_errors: Set tracking already seen errors, extended in-place
    """
    if errors_elem is None:
        return

    for error in errors_elem:
        if error.tag != "error":
            continue
        error_key = _create_error_key(error)
        if error_key not in seen_errors:
            seen_errors.add(error_key)
            merged_errors.append(error)


def _merge_simple_section(
    source_elem: ET.Element | None, target_elem: ET.Element
) -> None:
    """
    Merge an XML section without deduplication.

    Args:
        source_elem: Source XML element
        target_elem: Target XML element to append children to
    """
    if source_elem is not None:
        for child in source_elem:
            target_elem.append(child)


def _merge_checkers(
    checkers_elem: ET.Element | None,
    merged_checkers: ET.Element,
    seen_checkers: set,
) -> None:
    """
    Merge checker elements with deduplication.

    Args:
        checkers_elem: Source checkers-report XML element
        merged_checkers: Target merged checkers-report XML element
        seen_checkers: Set tracking already seen checker IDs, extended in-place
    """
    if checkers_elem is None:
        return

    for checker in checkers_elem:
        if checker.tag != "checker":
            continue
        checker_id = checker.get("id")
        if checker_id and checker_id not in seen_checkers:
            seen_checkers.add(checker_id)
            merged_checkers.append(checker)


def _copy_cppcheck_info(root: ET.Element, merged_root: ET.Element) -> bool:
    """
    Copy the cppcheck metadata element from a report into the merged report.

    Args:
        root: Source XML root element
        merged_root: Target merged XML root element

    Returns:
        True if metadata was copied, False if the source carries none
    """
    cppcheck_source = root.find("cppcheck")
    if cppcheck_source is not None:
        cppcheck_elem = ET.SubElement(merged_root, "cppcheck")
        cppcheck_elem.attrib.update(cppcheck_source.attrib)
        return True
    return False


def merge_reports(report_files: list[Path]) -> ET.Element:
    """
    Merge multiple cppcheck XML reports into one.

    Args:
        report_files: Paths of the cppcheck XML reports to merge

    Returns:
        Merged XML root element containing all reports
    """
    merged_root = ET.Element("results", version="3")

    merged_errors = ET.SubElement(merged_root, "errors")
    merged_safety = ET.SubElement(merged_root, "safety")
    merged_critical_errors = ET.SubElement(merged_root, "critical-errors")
    merged_checkers_report = ET.SubElement(merged_root, "checkers-report")
    merged_metrics = ET.SubElement(merged_root, "metrics")

    seen_checkers: set = set()
    seen_errors: set = set()
    cppcheck_copied = False

    for report_file in report_files:
        print(f"Processing: {report_file}")
        root = parse_xml_report(report_file)
        if root is None:
            continue

        if not cppcheck_copied:
            cppcheck_copied = _copy_cppcheck_info(root, merged_root)

        _merge_errors(root.find("errors"), merged_errors, seen_errors)
        _merge_simple_section(root.find("safety"), merged_safety)
        _merge_simple_section(root.find("critical-errors"), merged_critical_errors)
        _merge_checkers(
            root.find("checkers-report"), merged_checkers_report, seen_checkers
        )
        _merge_simple_section(root.find("metrics"), merged_metrics)

    return merged_root


def write_merged_report(merged_root: ET.Element, output_file: Path) -> None:
    """
    Write the merged report to an XML file.

    Args:
        merged_root: Merged XML root element
        output_file: Path to write the merged report to
    """
    ET.indent(merged_root, space="    ")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(merged_root).write(
        output_file, encoding="UTF-8", xml_declaration=True
    )
    print(f"Merged report written to: {output_file}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the merge.

    Args:
        argv: Argument list without the program name, or None to read sys.argv.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Merge the cppcheck XML reports of a Bazel build into a single consolidated report."
    )
    parser.add_argument(
        "--build-event-json-file",
        type=Path,
        required=True,
        help="Path to the Bazel build event JSON file (passed via --build_event_json_file to bazel build)",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root used to resolve relative paths from the build event JSON file (default: the current working directory)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("cppcheck-report.xml"),
        help="Output file path for the merged XML report (default: cppcheck-report.xml)",
    )

    args = parser.parse_args(argv)

    report_files = files_from_bep(
        build_event_json_file=args.build_event_json_file,
        workspace_root=args.workspace_root,
        suffix=CPPCHECK_XML_SUFFIX,
    )

    if not report_files:
        print(
            f"Error: No cppcheck XML reports listed in {args.build_event_json_file}",
            file=sys.stderr,
        )
        return 1

    print(f"Found {len(report_files)} report files:")
    for report_file in report_files:
        print(f"  - {report_file}")

    merged_root = merge_reports(report_files)
    write_merged_report(merged_root, args.output_file)

    errors_count = len(merged_root.find("errors"))
    metrics_count = len(merged_root.find("metrics"))
    print(
        f"Merged {len(report_files)} files with {errors_count} total errors and {metrics_count} metrics"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
