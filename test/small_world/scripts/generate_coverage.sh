#!/bin/bash

set -e

OPEN_REPORT=false
CREATE_ARCHIVE=false

for arg in "$@"; do
    case $arg in
        --open)
            OPEN_REPORT=true
            ;;
        --archive)
            CREATE_ARCHIVE=true
            ;;
    esac
done

echo "Generating coverage report..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS - using coverage configuration for Mac"
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
    "$(bazel info output_path)/_coverage/_coverage_report.dat"

echo "Coverage report generated in cov_html/"

if [[ "$CREATE_ARCHIVE" == true ]]; then
    echo "Creating archive cov_html.tar.gz..."
    tar -czf cov_html.tar.gz cov_html
    echo "Archive created: cov_html.tar.gz"
fi

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