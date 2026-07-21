#!/bin/bash
# Generic valgrind callgrind runner used by swift_add_valgrind_callgrind targets.
# Arguments are forwarded to valgrind:
#   [valgrind_flags...] binary [binary_args...]
#
# The tokens {OUTPUT_DIR} and {TMPDIR} in the forwarded arguments are replaced
# with TEST_UNDECLARED_OUTPUTS_DIR and TEST_TMPDIR respectively, letting the
# caller route a binary's output/working directory to a writable location.
#
# Outputs written to TEST_UNDECLARED_OUTPUTS_DIR:
#   valgrind-callgrind.<pid>          — raw callgrind output per process
#                                       (inspect with KCacheGrind)
#   valgrind-callgrind.instructions   — total instruction count summed over all
#                                       processes (single line)
# The %p (pid) suffix keeps output from separate processes distinct when
# --trace-children=yes is used.

set -euo pipefail

OUTPUT_DIR="${TEST_UNDECLARED_OUTPUTS_DIR:-$(mktemp -d)}"
SCRATCH_DIR="${TEST_TMPDIR:-$(mktemp -d)}"
CALLGRIND_OUT_PATTERN="${OUTPUT_DIR}/valgrind-callgrind.%p"
INSTRUCTIONS_FILE="${OUTPUT_DIR}/valgrind-callgrind.instructions"

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

# Sum the instruction count across every process's output file. callgrind
# reports the total on a "summary:" line (or "totals:" in older formats); the
# first field is the instruction count (Ir).
TOTAL_INSTRUCTIONS=0
FOUND=0
for f in "${OUTPUT_DIR}"/valgrind-callgrind.*; do
    [ -e "$f" ] || continue
    n=$(awk '/^summary:/{print $2; exit}' "$f")
    if [ -z "$n" ]; then
        n=$(awk -F: '/^totals:/{gsub(/ /, "", $2); print $2; exit}' "$f")
    fi
    [ -n "$n" ] || continue
    TOTAL_INSTRUCTIONS=$((TOTAL_INSTRUCTIONS + n))
    FOUND=1
done

if [ "$FOUND" -eq 0 ]; then
    echo "Error: no callgrind output files found in $OUTPUT_DIR" >&2
    exit 1
fi

echo "$TOTAL_INSTRUCTIONS" > "$INSTRUCTIONS_FILE"
echo "CPU instructions: $TOTAL_INSTRUCTIONS"
