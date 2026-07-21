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
#   callgrind.out         — raw callgrind output (inspect with KCacheGrind)
#   cpu_instructions.txt  — total instruction count (single line)

set -euo pipefail

OUTPUT_DIR="${TEST_UNDECLARED_OUTPUTS_DIR:-$(mktemp -d)}"
SCRATCH_DIR="${TEST_TMPDIR:-$(mktemp -d)}"
CALLGRIND_OUT="${OUTPUT_DIR}/callgrind.out"

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
    "--callgrind-out-file=${CALLGRIND_OUT}" \
    "${ARGS[@]}"

if [ ! -f "$CALLGRIND_OUT" ]; then
    echo "Error: callgrind output file not found: $CALLGRIND_OUT" >&2
    exit 1
fi

CPU_INSTRUCTIONS=$(awk '/^summary:/{print $2; exit}' "$CALLGRIND_OUT")
if [ -z "$CPU_INSTRUCTIONS" ]; then
    CPU_INSTRUCTIONS=$(awk -F: '/^totals:/{gsub(/ /, "", $2); print $2; exit}' "$CALLGRIND_OUT")
fi

echo "$CPU_INSTRUCTIONS" > "${OUTPUT_DIR}/cpu_instructions.txt"
echo "CPU instructions: $CPU_INSTRUCTIONS"
