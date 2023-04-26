#!/bin/bash

# This script compares the bazel_test_srcs.txt and
# build/cmake_test_srcs.txt files, which contain Bazel and CMake test
# source files, respectively.
# Usage: compare_test_srcs <IGNORED_FILES>

ignored_files=$(cat $1)

cd $BUILD_WORKSPACE_DIRECTORY

if [ ! -f bazel_test_srcs.txt ]; then
    echo "bazel_test_srcs.txt file not found"
    exit 1
fi

if [ ! -f build/cmake_test_srcs.txt ]; then
    echo "build/cmake_test_srcs.txt file not found"
    exit 1
fi

flags=""

for f in $ignored_files
do
    flags="$flags -I ^$f$"
done

if ! results=$(diff $flags bazel_test_srcs.txt build/cmake_test_srcs.txt); then
    i=0
    for result in $results
    do
        if [[ $(( i % 3 )) == 1 ]]; then
            if [[ "$result" == ">" ]]; then
                echo -n "Bazel doesn't have: "
            else
                echo -n "CMake doesn't have: "
            fi
        elif [[ $(( i % 3 )) == 2 ]]; then
            echo $result
        fi
        i=$((i+1))
    done
    exit 1
fi
