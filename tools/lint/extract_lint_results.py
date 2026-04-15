#!/usr/bin/env python3
"""
Extract and merge linting results from a Bazel build.

Collects SARIF (Static Analysis Results Interchange Format) report files and
patch files from a Bazel Build Event Protocol JSON file, merges the SARIF
reports into a single file for efficient processing by reviewdog, and copies
non-empty patch files to a specified directory.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


def extract_files_from_bep(
    build_event_json_file: Path,
    bazel_output_path: Path,
    ext: str,
) -> list[Path]:
    """
    Extract file paths with the given extension from a Bazel Build Event Protocol JSON file.

    The BEP file is newline-delimited JSON. Each line is parsed for namedSetOfFiles
    entries, and files whose name ends with the given extension are collected.

    Args:
        build_event_json_file: Path to the Bazel build event JSON file
        ext: File extension to filter
        bazel_output_path: Workspace root used to resolve relative BEP paths
            (e.g. paths starting with bazel-out/). When omitted, paths are kept
            as-is (relative to the current working directory).

    Returns:
        List of matching file paths
    """
    report_files = []

    with open(build_event_json_file, "r") as f:
        for line in f:
            line = line.strip().rstrip("\r")
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"Error: Build event JSON file contains errors: {build_event_json_file}",
                    file=sys.stderr,
                )
                sys.exit(1)

            named_set = event.get("namedSetOfFiles")
            if named_set is None:
                continue

            for file_info in named_set.get("files", []):
                name = file_info.get("name", "")
                if name.endswith(ext):
                    path_prefix = file_info.get("pathPrefix", [])
                    path = Path("/".join(path_prefix) + "/" + name)
                    if not path.is_absolute() and bazel_output_path is not None:
                        path = bazel_output_path / path
                    report_files.append(path)

    return report_files


def normalize_path(uri: str, workspace_root: Path | None = None) -> str:
    """
    Normalize Bazel execroot paths to repository-relative paths.

    Strips Bazel's execroot structure (e.g., '../../../902/execroot/_main/')
    to make paths relative to the repository root for reviewdog.
    Also resolves Bazel _virtual_includes symlinks created by strip_include_prefix.

    Args:
        uri: Original URI from SARIF report
        workspace_root: Repository root used to resolve _virtual_includes symlinks

    Returns:
        Normalized path relative to repository root
    """
    # Pattern to match Bazel execroot paths like:
    # ../../../902/execroot/_main/lib1/...
    # ../../execroot/_main/lib1/...
    # The pattern captures everything after 'execroot/_main/' or 'execroot/__main__/'
    execroot_pattern = r"(?:\.\./)*(?:\d+/)?execroot/(?:_main|__main__)/(.*)"

    match = re.match(execroot_pattern, uri)
    if match:
        normalized = match.group(1)
    else:
        # If no execroot pattern found, return the URI as-is
        # but strip leading '../' if present
        normalized = uri.lstrip("../")

    # Resolve _virtual_includes symlinks produced by strip_include_prefix.
    # Bazel creates a symlink forest under bazel-out/.../bin/<pkg>/_virtual_includes/
    # pointing back into the real source tree. Follow the symlink so that the
    # resulting path matches the PR diff (e.g. lib1/include/foo.h instead of
    # bazel-out/.../lib1/_virtual_includes/foo.h).
    if "_virtual_includes" in normalized and workspace_root is not None:
        full_path = workspace_root / normalized
        try:
            resolved = Path(os.path.realpath(full_path))
            canonical_root = Path(os.path.realpath(workspace_root))
            normalized = str(resolved.relative_to(canonical_root))
        except (OSError, ValueError):
            pass  # Keep original if the symlink cannot be resolved

    return normalized


def normalize_sarif_paths(
    run: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """
    Normalize all file paths in a SARIF run to be repository-relative.

    Args:
        run: A SARIF run object
        workspace_root: Repository root used to resolve _virtual_includes symlinks

    Returns:
        The run object with normalized paths
    """
    # Normalize paths in results
    artifacts = (
        loc.get("physicalLocation", {}).get("artifactLocation")
        for res in run.get("results", [])
        for loc in res.get("locations", [])
    )

    for artifact in artifacts:
        if artifact and "uri" in artifact:
            artifact["uri"] = normalize_path(artifact["uri"], workspace_root)
            artifact.pop("uriBaseId", None)

    return run


def filter_external_dependencies(run: dict[str, Any]) -> dict[str, Any]:
    """
    Remove results whose primary location points to a Bazel external dependency.

    Bazel downloads external repositories (Eigen, Abseil, etc.) into a directory
    that is only reachable through the Bazel execroot symlink.  Inside Docker the
    bazel-out symlink is broken, so SonarCloud cannot resolve these paths and
    falls back to project-level issues with no source context.  Dropping them
    here keeps the report clean and avoids misleading project-level noise.

    After normalize_sarif_paths the affected URIs start with 'external/'.

    Args:
        run: A SARIF run object

    Returns:
        The run object with external-dependency results removed
    """
    if "results" not in run:
        return run
    run["results"] = [
        result
        for result in run["results"]
        if not result.get("locations", [{}])[0]
        .get("physicalLocation", {})
        .get("artifactLocation", {})
        .get("uri", "")
        .startswith("external/")
    ]
    return run


def filter_errors_only(run: dict[str, Any]) -> dict[str, Any]:
    """
    Filter a SARIF run to only keep results with level "error".

    Args:
        run: A SARIF run object

    Returns:
        The run object with only error-level results
    """
    if "results" in run:
        run["results"] = [
            result for result in run["results"] if result.get("level") == "error"
        ]
    return run


_CHECK_RE = re.compile(r"\[([a-zA-Z0-9_\-\.]+)\]$")


def extract_rule_ids(run: dict[str, Any]) -> dict[str, Any]:
    """
    Backfill ruleId on SARIF results that are missing it.

    clang-tidy embeds the check name at the end of each message as [check-name]
    but does not populate the SARIF ruleId field.  SonarQube silently drops any
    result that lacks a ruleId, so this function extracts the check name from
    the message text and sets it as ruleId.

    Also populates the tool.driver.rules array so SonarQube can resolve rule
    metadata even when the original SARIF driver section lists no rules.

    Args:
        run: A SARIF run object (mutated in-place)

    Returns:
        The same run object with ruleId fields filled in
    """
    known_rules: dict[str, dict[str, Any]] = {
        r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])
    }

    for result in run.get("results", []):
        if "ruleId" in result:
            continue
        msg = result.get("message", {}).get("text", "").strip()
        m = _CHECK_RE.search(msg)
        if m:
            rule_id = m.group(1)
            result["ruleId"] = rule_id
            if rule_id not in known_rules:
                # Carry the SARIF level into defaultConfiguration so SonarQube
                # can use it as the rule severity instead of defaulting to MEDIUM.
                level = result.get("level", "warning")
                known_rules[rule_id] = {
                    "id": rule_id,
                    "defaultConfiguration": {"level": level},
                }

    run.setdefault("tool", {}).setdefault("driver", {})["rules"] = list(
        known_rules.values()
    )
    return run


def deduplicate_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Deduplicate results across a list of SARIF runs.

    Header files are included by multiple .cc compilation units, producing one
    clang-tidy run per including file and therefore one copy of each header
    diagnostic per includer. This function collapses those duplicates, keying
    on (uri, startLine, startColumn, ruleId).

    Args:
        runs: List of SARIF run objects (may contain duplicate results)

    Returns:
        The same list of runs with duplicate results removed. Duplicates are
        dropped from later runs; the first occurrence is kept.
    """
    seen: set[tuple[str, int, int, str]] = set()
    for run in runs:
        unique = []
        for result in run.get("results", []):
            phys = result.get("locations", [{}])[0].get("physicalLocation", {})
            uri = phys.get("artifactLocation", {}).get("uri", "")
            region = phys.get("region", {})
            key = (
                uri,
                region.get("startLine", 0),
                region.get("startColumn", 0),
                result.get("ruleId", ""),
            )
            if key not in seen:
                seen.add(key)
                unique.append(result)
        if "results" in run:
            run["results"] = unique
    return runs


def collect_and_merge_sarif(
    build_event_json_file: Path,
    output_merged_sarif_file: Path,
    bazel_output_path: Path,
    only_errors: bool = False,
) -> int:
    """
    Find all .report files from the BEP file and merge them into a single SARIF file.

    Args:
        build_event_json_file: Path to the Bazel build event JSON file
        output_merged_sarif_file: Output path for the merged SARIF report
        bazel_output_path: Workspace root used to resolve relative BEP paths
        only_errors: If True, filter results to only include error-level findings

    Returns:
        Total number of results in the merged report
    """
    report_files = extract_files_from_bep(
        build_event_json_file=build_event_json_file,
        bazel_output_path=bazel_output_path,
        ext=".report",
    )
    print(f"Found {len(report_files)} .report files from build events")
    for report in report_files:
        print(f"  - {report}")

    return merge_sarif_reports(
        input_files=report_files,
        output_file=output_merged_sarif_file,
        only_errors=only_errors,
        workspace_root=bazel_output_path,
    )


def collect_patches(
    build_event_json_file: Path,
    output_patch_folder: Path,
    bazel_output_path: Path,
) -> None:
    """
    Copy non-empty patch files listed in the BEP file to the given folder.

    Args:
        build_event_json_file: Path to the Bazel build event JSON file
        output_patch_folder: Directory to copy patch files into
        bazel_output_path: Workspace root used to resolve relative BEP paths
    """
    patch_files = extract_files_from_bep(
        build_event_json_file,
        bazel_output_path=bazel_output_path,
        ext=".patch",
    )
    output_patch_folder.mkdir(parents=True, exist_ok=True)
    copied = 0
    for patch in patch_files:
        if patch.exists() and patch.stat().st_size > 0:
            dest = output_patch_folder / patch.name
            dest.unlink(missing_ok=True)
            shutil.copy2(patch, dest)
            copied += 1
    if copied > 0:
        print(f"Copied {copied} patch file(s) to {output_patch_folder}")


def merge_sarif_reports(
    input_files: list[Path],
    output_file: Path,
    only_errors: bool = False,
    workspace_root: Path | None = None,
) -> int:
    """
    Merge multiple SARIF report files into a single SARIF file.
    Normalizes Bazel execroot paths to repository-relative paths.

    Args:
        input_files: List of paths to input SARIF files
        output_file: Path to write the merged SARIF file
        only_errors: If True, filter results to only include error-level findings
        workspace_root: Repository root used to resolve _virtual_includes symlinks
    """
    if not input_files:
        print("No input files to merge", file=sys.stderr)
        # Create an empty but valid SARIF file
        merged_sarif: dict[str, Any] = {"version": "2.1.0", "runs": []}
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(merged_sarif, f, indent=2)
        print(f"Created empty SARIF report at {output_file}")
        return 0

    merged_runs = []
    schema_version = "2.1.0"
    schema_uri = None
    processed_files = 0
    normalized_paths = 0

    for input_file in input_files:
        if not input_file.exists() or input_file.stat().st_size == 0:
            print(f"Skipping empty or non-existent file: {input_file}", file=sys.stderr)
            continue

        try:
            with open(input_file, "r") as f:
                data = json.load(f)

            # Extract schema information from first valid file
            if schema_uri is None and "$schema" in data:
                schema_uri = data["$schema"]

            if "version" in data:
                schema_version = data["version"]

            # Collect all runs from this file and normalize paths
            if "runs" in data:
                for run in data["runs"]:
                    normalized_run = normalize_sarif_paths(run, workspace_root)
                    normalized_run = filter_external_dependencies(normalized_run)
                    normalized_run = extract_rule_ids(normalized_run)
                    if only_errors:
                        normalized_run = filter_errors_only(normalized_run)
                    results = normalized_run.get("results", [])
                    if not results:
                        continue
                    merged_runs.append(normalized_run)
                    normalized_paths += len(results)
                processed_files += 1

        except Exception as e:
            print(
                f"Error processing {input_file}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Create the merged SARIF structure; filter out any runs left empty by deduplication
    merged_sarif = {
        "version": schema_version,
        "runs": [r for r in deduplicate_runs(merged_runs) if r.get("results")],
    }

    if schema_uri:
        merged_sarif["$schema"] = schema_uri

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write the merged file
    with open(output_file, "w") as f:
        json.dump(merged_sarif, f, indent=2)

    print(
        f"Successfully merged {len(merged_runs)} runs from {processed_files} files into {output_file}"
    )
    print(f"Normalized paths for {normalized_paths} results")
    return normalized_paths


def main():
    parser = argparse.ArgumentParser(
        description="Collect and merge SARIF report files from a Bazel Build Event Protocol JSON file into a single file."
    )
    parser.add_argument(
        "--build-event-json-file",
        type=Path,
        required=True,
        help="Path to the Bazel build event JSON file (passed via --build-event-json-file to bazel build)",
    )
    parser.add_argument(
        "--bazel-output-path",
        type=Path,
        required=True,
        help="Workspace root used to resolve relative paths from the build event JSON file (e.g. $(pwd) when invoking from the repo root)",
    )
    parser.add_argument(
        "--output-merged-sarif-file",
        type=Path,
        default=None,
        help="Output file path for the merged SARIF report (e.g., sarif-reports/merged-report.sarif)",
    )
    parser.add_argument(
        "--exit-code",
        type=int,
        default=None,
        help="Exit with this code if any errors are found in the merged report",
    )
    parser.add_argument(
        "--only-errors",
        action="store_true",
        default=False,
        help="Keep only error-level results in the merged report, removing warnings and other findings",
    )
    parser.add_argument(
        "--output-patch-folder",
        type=Path,
        default=None,
        help="Directory to collect non-empty patch files from the build event JSON file",
    )

    args = parser.parse_args()

    if not args.build_event_json_file.exists():
        print(
            f"Error: Build event JSON file does not exist: {args.build_event_json_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    total_results = 0
    if args.output_merged_sarif_file is not None:
        total_results = collect_and_merge_sarif(
            build_event_json_file=args.build_event_json_file,
            output_merged_sarif_file=args.output_merged_sarif_file,
            bazel_output_path=args.bazel_output_path,
            only_errors=args.only_errors,
        )

    if args.output_patch_folder is not None:
        collect_patches(
            build_event_json_file=args.build_event_json_file,
            output_patch_folder=args.output_patch_folder,
            bazel_output_path=args.bazel_output_path,
        )

    if args.exit_code is not None and total_results > 0:
        sys.exit(args.exit_code)


if __name__ == "__main__":
    main()
