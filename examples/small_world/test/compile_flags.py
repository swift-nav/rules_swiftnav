#!/usr/bin/env python3
"""
Script to generate compile_commands.json and analyze compile flags for duplicates.
"""

import argparse
import json
import subprocess
import sys
from collections import Counter


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate compile_commands.json and analyze compile flags"
    )
    parser.add_argument(
        "filename",
        nargs="?",
        default="src/base_math/base_math.cc",
        help="Source file to analyze (default: src/base_math/base_math.cc)"
    )
    args = parser.parse_args()

    print("Running: bazel run @hedron_compile_commands//:refresh_all")
    print("-" * 60)

    # Execute the bazel command
    try:
        result = subprocess.run(
            ["bazel", "run", "@hedron_compile_commands//:refresh_all"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error running bazel command: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Reading compile_commands.json...")
    print("=" * 60 + "\n")

    # Read the generated compile_commands.json
    try:
        with open("compile_commands.json", "r") as f:
            compile_commands = json.load(f)
    except FileNotFoundError:
        print("Error: compile_commands.json not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing compile_commands.json: {e}", file=sys.stderr)
        sys.exit(1)

    if not compile_commands:
        print("Error: compile_commands.json is empty", file=sys.stderr)
        sys.exit(1)

    # Find the entry for the specified file
    target_entry = None
    for entry in compile_commands:
        if entry.get("file", "").endswith(args.filename):
            target_entry = entry
            break

    if not target_entry:
        print(f"Error: No entry found for file '{args.filename}'", file=sys.stderr)
        print(f"\nAvailable files:", file=sys.stderr)
        for entry in compile_commands[:5]:
            print(f"  - {entry.get('file', 'N/A')}", file=sys.stderr)
        if len(compile_commands) > 5:
            print(f"  ... and {len(compile_commands) - 5} more", file=sys.stderr)
        sys.exit(1)

    print(f"Target file: {target_entry.get('file', 'N/A')}")
    print(f"Directory: {target_entry.get('directory', 'N/A')}")
    print("\n" + "-" * 60)
    print("Compile options from target entry:")
    print("-" * 60 + "\n")

    # Parse the command to extract compile options
    command = target_entry.get("command", "")
    if not command:
        # Try 'arguments' field if 'command' is not present
        arguments = target_entry.get("arguments", [])
        if arguments:
            compile_options = [arg for arg in arguments if arg.startswith("-")]
        else:
            print("Error: No command or arguments found in target entry", file=sys.stderr)
            sys.exit(1)
    else:
        # Split command string and extract options starting with '-'
        import shlex
        parts = shlex.split(command)
        compile_options = [part for part in parts if part.startswith("-")]

    # Display all compile options
    for i, option in enumerate(compile_options, 1):
        print(f"{i:3d}. {option}")

    print(f"\nTotal compile options: {len(compile_options)}")

    # Check for duplicates
    print("\n" + "=" * 60)
    print("Checking for duplicate compile options...")
    print("=" * 60 + "\n")

    option_counts = Counter(compile_options)
    duplicates = {opt: count for opt, count in option_counts.items() if count > 1}

    if duplicates:
        print(f"Found {len(duplicates)} duplicate compile option(s):\n")
        for option, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
            print(f"  '{option}' appears {count} times")
    else:
        print("No duplicate compile options found.")

    # Check for contradicting flags
    print("\n" + "=" * 60)
    print("Checking for contradicting compile options...")
    print("=" * 60 + "\n")

    contradictions_found = False

    # Check for multiple -std= flags
    std_flags = [opt for opt in compile_options if opt.startswith("-std=")]
    if len(std_flags) > 1:
        contradictions_found = True
        print(f"Found {len(std_flags)} conflicting C++ standard flags:")
        for flag in std_flags:
            print(f"  {flag}")
        print()

    # Check for multiple optimization levels
    opt_flags = [opt for opt in compile_options if opt in ["-O0", "-O1", "-O2", "-O3", "-Os", "-Oz", "-Og", "-Ofast"]]
    if len(opt_flags) > 1:
        contradictions_found = True
        print(f"Found {len(opt_flags)} conflicting optimization level flags:")
        for flag in opt_flags:
            print(f"  {flag}")
        print()

    # Check for conflicting debug flags
    if "-g" in compile_options and "-g0" in compile_options:
        contradictions_found = True
        print("Found conflicting debug flags:")
        print("  -g (enable debug info)")
        print("  -g0 (disable debug info)")
        print()

    # Check for conflicting warning flags
    warning_contradictions = []
    for i, opt1 in enumerate(compile_options):
        if opt1.startswith("-W") and not opt1.startswith("-Wl,"):
            # Check if there's a negating flag
            if opt1.startswith("-Wno-"):
                positive_flag = "-W" + opt1[5:]  # Remove "no-" to get positive version
                if positive_flag in compile_options:
                    warning_contradictions.append((positive_flag, opt1))
            else:
                negative_flag = opt1[:2] + "no-" + opt1[2:]  # Add "no-"
                if negative_flag in compile_options:
                    warning_contradictions.append((opt1, negative_flag))

    # Remove duplicates by converting to set
    warning_contradictions = list(set(warning_contradictions))

    if warning_contradictions:
        contradictions_found = True
        print(f"Found {len(warning_contradictions)} conflicting warning flag pair(s):")
        for pos_flag, neg_flag in warning_contradictions:
            print(f"  {pos_flag} <-> {neg_flag}")
        print()

    if not contradictions_found:
        print("No contradicting compile options found.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
