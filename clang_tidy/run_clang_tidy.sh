#! /bin/bash
# Usage: run_clang_tidy <CONFIG> <OUTPUT> [ARGS...]
set -ue

CLANG_TIDY_BIN=$1
shift

CONFIG=$1
shift

OUTPUT=$1
shift

echo "Running clang-tidy with config $CONFIG"

# .clang-tidy config file has to be placed in the current working directory
#if [ ! -f ".clang-tidy" ]; then
#ln -s $CONFIG .clang-tidy
#fi

# clang-tidy doesn't create a patchfile if there are no errors.
# make sure the output exists, and empty if there are no errors,
# so the build system will not be confused.
touch $OUTPUT
truncate -s 0 $OUTPUT

#echo "${CLANG_TIDY_BIN}" -config-file $CONFIG "$@"
"${CLANG_TIDY_BIN}" -config-file $CONFIG "$@"

test ! -s $OUTPUT
