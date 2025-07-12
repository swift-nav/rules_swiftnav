#! /bin/bash
# Usage: run_clang_tidy <CONFIG> <OUTPUT> [ARGS...]
set -ue

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

# bazel runs clang-tidy in the sandbox so any diagnostics will contain
# paths relative to the sandbox. We need to strip the sandbox prefix
# from the paths so that the output matches the source tree and can
# be understood by other tools such as IDEs.
"${CLANG_TIDY_BIN}" "$@" | sed "s;.*execroot/[^/]*/;;"
sed -i "s;.*execroot/[^/]*/;;" $OUTPUT

test ! -s $OUTPUT
