#!/bin/bash

set -e

OPEN_REPORT=false

for arg in "$@"; do
    case $arg in
        --open)
            OPEN_REPORT=true
            ;;
    esac
done

echo "Generating coverage report..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS - using coverage configuration for Mac"
    export JAVA_HOME=$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk/Contents/Home
    bazel coverage --config=cov_mac //...
else
    echo "Running coverage for non-Mac platform"
    bazel coverage //...
fi
