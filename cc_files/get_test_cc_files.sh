#!/bin/bash

cd $BUILD_WORKSPACE_DIRECTORY

bazel build --aspects @rules_swiftnav//cc_files:get_cc_files.bzl%get_cc_test_srcs --output_groups=report //...
find ./bazel-out/ -type f -regex ".*_test_srcs\.txt" -exec cat {} + | sort > bazel_test_srcs.txt

echo "Test sources are stored in the $PWD/bazel_test_srcs.txt file"
