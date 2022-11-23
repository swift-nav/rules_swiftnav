#! /bin/bash
# Usages:
# run_clang_format format_all <CLANG_FORMAT_BIN> <CLANG_FORMAT_CONFIG>
# run_clang_format check_file <CLANG_FORMAT_BIN> <INPUT> <OUTPUT>
set -ue

format_all() {
    CLANG_FORMAT_CONFIG=$(realpath $1)

    cd $BUILD_WORKSPACE_DIRECTORY
    if ! test -f .clang-format; then
        echo ".clang-format file not found. Bazel will copy the default .clang-format file."
        cp $CLANG_FORMAT_CONFIG .
    fi
    git describe --tags --abbrev=0 --always \
    | xargs -I % git diff --diff-filter=ACMRTUXB --name-only --line-prefix=`git rev-parse --show-toplevel`/ % -- '*.[ch]' '*.cpp' '*.cc' '*.hpp' \
    | xargs clang-format-14 -i
}

check_file() {
    INPUT=$1
    OUTPUT=$2

    $CLANG_FORMAT_BIN $INPUT --dry-run -Werror > $OUTPUT
}

ARG=$1
CLANG_FORMAT_BIN=$(realpath $2)
shift 2

if [ "$ARG" == "format_all" ]; then
    format_all "$@"
elif [ "$ARG" == "check_file" ]; then
    check_file "$@"
fi
