#! /bin/bash
# Usages:
# run_clang_format format_all <CLANG_FORMAT_BIN>
# run_clang_format check_file <CLANG_FORMAT_BIN> <INPUT> <OUTPUT>
set -ue

format_all() {
    cd $BUILD_WORKSPACE_DIRECTORY
    git ls-files '*.[ch]' '*.cpp' '*.cc' '*.hpp' | xargs $CLANG_FORMAT_BIN -i
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
    format_all
elif [ "$ARG" == "check_file" ]; then
    check_file "$@"
fi
