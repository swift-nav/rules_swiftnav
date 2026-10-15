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
    export JAVA_HOME=$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk/Contents/Home
fi

bazel coverage //...
