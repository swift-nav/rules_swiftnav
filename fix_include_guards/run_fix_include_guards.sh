#! /bin/bash
set -ue

: "${BUILD_WORKSPACE_DIRECTORY:=./}"

fix_include_guards() {
    cd $BUILD_WORKSPACE_DIRECTORY
    python fix_include_guards.py `git ls-files '*.h'`
}

diff_check() {
    fix_include_guards
    git diff --exit-code
}

if [ "$#" -ge 1 ] && [ "$1" == "check" ]; then
    diff_check
else
    fix_include_guards
fi
