#! /bin/bash
# Usages:
# run_clang_format format_all <CLANG_FORMAT_BIN> <CLANG_FORMAT_CONFIG>
# run_clang_format check_file <CLANG_FORMAT_BIN> <CLANG_FORMAT_CONFIG> <INPUT> <OUTPUT>
set -ue

format_all() {
    CLANG_FORMAT_CONFIG=$(realpath $1)

    cd $BUILD_WORKSPACE_DIRECTORY
    git ls-files '*.[ch]' '*.cpp' '*.cxx' '*.cc' '*.hpp' '*.hxx' \
    | xargs -r $CLANG_FORMAT_BIN -i --style=file:$CLANG_FORMAT_CONFIG
}

format_diff() {
    CLANG_FORMAT_CONFIG=$(realpath $1)

    cd $BUILD_WORKSPACE_DIRECTORY
    git describe --tags --abbrev=0 --always \
    | xargs -rI % git diff --diff-filter=ACMRTUXB --name-only --line-prefix=`git rev-parse --show-toplevel`/ % -- '*.[ch]' '*.cpp' '*.cxx' '*.cc' '*.hpp' '*.hxx' \
    | xargs -r $CLANG_FORMAT_BIN -i --style=file:$CLANG_FORMAT_CONFIG
}

check_file() {
    CONFIG=$1
    INPUT=$2
    OUTPUT=$3

    # .clang-format config file has to be placed in the current working directory
    if [ ! -f ".clang-format" ]; then
        ln -s $CONFIG .clang-format
    fi

    $CLANG_FORMAT_BIN $INPUT --dry-run -Werror > $OUTPUT
}

ARG=$1
CLANG_FORMAT_BIN=$(realpath $2)
shift 2

if [ "$ARG" == "format_diff" ]; then
    format_diff "$@"
elif [ "$ARG" == "format_all" ]; then
    format_all "$@"
elif [ "$ARG" == "check_file" ]; then
    check_file "$@"
fi
