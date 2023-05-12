#!/bin/bash

cd $BUILD_WORKSPACE_DIRECTORY

find ./bazel-out/ -path '*bazel_clang_tidy_*.clang-tidy.yaml' -exec cat {} + > clang_tidy_fixes.txt

echo "Clang tidy fixes are stored in the $PWD/clang_tidy_fixes.txt file"
