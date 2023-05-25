#! /bin/bash
# Usage: run_clang_tidy <CONFIG> <OUTPUT> [ARGS...]
set -ue

# Necessary for clang-tidy to find system headers on mac
export SDKROOT="/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"

CLANG_TIDY_BIN=$1
shift

CONFIG=$1
shift

OUTPUT=$1
shift

# .clang-tidy config file has to be placed in the current working directory
if [ ! -f ".clang-tidy" ]; then
    ln -s $CONFIG .clang-tidy
fi

# clang-tidy doesn't create a patchfile if there are no errors.
# make sure the output exists, and empty if there are no errors,
# so the build system will not be confused.
touch $OUTPUT
truncate -s 0 $OUTPUT

"${CLANG_TIDY_BIN}" "$@"

test ! -s $OUTPUT
