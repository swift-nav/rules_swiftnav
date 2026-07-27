#!/bin/bash
# Runs valgrind callgrind for swift_add_valgrind_callgrind targets. Reporting
# and the baseline check live in the callgrind_report tool, whose runfiles path
# is the first argument; everything up to -- is forwarded to it.
#
# Usage:
#   valgrind_callgrind_run.sh <callgrind_report> [report_args...] -- \
#       [valgrind_flags...] binary [binary_args...]
#
# {OUTPUT_DIR} and {TMPDIR} in the valgrind arguments expand to
# TEST_UNDECLARED_OUTPUTS_DIR and TEST_TMPDIR. The %p (pid) suffix on the dumps
# keeps processes distinct under --trace-children=yes.

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Error: missing callgrind_report tool argument" >&2
    exit 1
fi

REPORT_TOOL="$(realpath "$1")"
shift

REPORT_ARGS=()
while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    REPORT_ARGS+=("$1")
    shift
done

if [ $# -eq 0 ]; then
    echo "Error: missing -- separator before the valgrind arguments" >&2
    exit 1
fi
shift

if [ $# -eq 0 ]; then
    echo "Error: no binary to run under callgrind" >&2
    exit 1
fi

OUTPUT_DIR="${TEST_UNDECLARED_OUTPUTS_DIR:-$(mktemp -d)}"
SCRATCH_DIR="${TEST_TMPDIR:-$(mktemp -d)}"
CALLGRIND_OUT_PATTERN="${OUTPUT_DIR}/valgrind-callgrind.%p"

if ! command -v valgrind &>/dev/null; then
    echo "Error: valgrind not found" >&2
    exit 1
fi

if [ "$(uname)" != "Linux" ]; then
    echo "Error: valgrind callgrind is only supported on Linux. Found OS: $(uname)" >&2
    exit 1
fi

# Substitute runtime tokens in the forwarded arguments.
ARGS=()
for a in "$@"; do
    a="${a//\{OUTPUT_DIR\}/$OUTPUT_DIR}"
    a="${a//\{TMPDIR\}/$SCRATCH_DIR}"
    ARGS+=("$a")
done

echo "Running callgrind profiling..."
valgrind -q --tool=callgrind \
    "--callgrind-out-file=${CALLGRIND_OUT_PATTERN}" \
    "${ARGS[@]}"

"$REPORT_TOOL" --output-dir "$OUTPUT_DIR" "${REPORT_ARGS[@]+"${REPORT_ARGS[@]}"}"
