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

echo "Generating HTML coverage report..."
bazel run @lcov//:genhtml -- \
    --output "$(pwd)/cov_html" \
    --source-directory="$(pwd)" \
    --branch-coverage \
    --ignore-errors inconsistent,gcov,unsupported,format,category,count,unused \
    --no-function-coverage \
    --flat \
    --legend \
    --quiet \
    "$(bazel info output_path)/_coverage/_coverage_report.dat"

echo "Coverage report generated in cov_html/"

if [[ "$OPEN_REPORT" == true ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Opening coverage report in default browser..."
        open "$(pwd)/cov_html/index.html"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Opening coverage report in default browser..."
        xdg-open "$(pwd)/cov_html/index.html"
    else
        echo "Coverage report available at: $(pwd)/cov_html/index.html"
    fi
fi
