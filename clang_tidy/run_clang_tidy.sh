#! /bin/bash
# Usage: run_clang_tidy <CONFIG> <OUTPUT> [ARGS...]
set -ue

CLANG_TIDY_BIN=$1
shift

CLANG_TIDY_CONFIG=$1
shift

CLANG_TIDY_OUTPUT=$1
shift

# clang-tidy doesn't create a patchfile if there are no errors.
# make sure the output exists, and empty if there are no errors,
# so the build system will not be confused.
touch $CLANG_TIDY_OUTPUT
truncate -s 0 $CLANG_TIDY_OUTPUT

"${CLANG_TIDY_BIN}" --config-file=$CLANG_TIDY_CONFIG "$@"

test ! -s $CLANG_TIDY_OUTPUT
