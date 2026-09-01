#!/usr/bin/env bash

set -euo pipefail

CREATE_PATCHES=false
APPLY_PATCHES=false
TARGETS=()
TARGETS_FILE=""

if [[ -z "${BUILD_WORKSPACE_DIRECTORY:-}" ]]; then
    echo "Environment variable BUILD_WORKSPACE_DIRECTORY is not set. Assuming ${PWD} is the workspace root."
    export BUILD_WORKSPACE_DIRECTORY="${PWD}"
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --create-patches)
            CREATE_PATCHES=true
            shift
            ;;
        --apply-patches)
            CREATE_PATCHES=true
            APPLY_PATCHES=true
            shift
            ;;
        --targets)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                TARGETS+=("$1")
                shift
            done
            ;;
        --targets-file)
            shift
            if [[ $# -eq 0 ]]; then
                echo "--targets-file requires a path"
                exit 1
            fi
            TARGETS_FILE="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -n "$TARGETS_FILE" ]]; then
    # Relative paths are meant from the workspace, not the runfiles directory
    # bazel run starts in. An empty file lints nothing rather than everything.
    if [[ "$TARGETS_FILE" != /* ]]; then
        TARGETS_FILE="$BUILD_WORKSPACE_DIRECTORY/$TARGETS_FILE"
    fi
    while IFS= read -r target || [[ -n "$target" ]]; do
        if [[ -n "$target" ]]; then
            TARGETS+=("$target")
        fi
    done <"$TARGETS_FILE"
elif [[ ${#TARGETS[@]} -eq 0 ]]; then
    TARGETS=("//...")
fi

buildevents=$(mktemp)
trap 'rm -f "$buildevents"' EXIT
echo "Build events in $buildevents"

args=(
    "--build_event_json_file=$buildevents"
    "--remote_download_regex=.*AspectRulesLint.*"
    "--config=lint"
    "--output_groups=rules_lint_machine"
    # rules_lint puts the human-readable report in the _validation output
    # group, which Bazel builds regardless of --output_groups. Without this,
    # clang-tidy runs twice per source file for a report nobody reads.
    "--norun_validations"
    "--keep_going"
)

if [[ "$CREATE_PATCHES" == true ]]; then
    args+=(
        "--@aspect_rules_lint//lint:fix"
        "--output_groups=rules_lint_patch"
    )
fi

# Run linters
(cd "$BUILD_WORKSPACE_DIRECTORY" && bazel build "${args[@]}" ${TARGETS[@]+"${TARGETS[@]}"})

OUTPUT_DIR="$BUILD_WORKSPACE_DIRECTORY/clang-tidy-output"
OUTPUT_DIR_MERGED_SARIF="$OUTPUT_DIR/merged-report.sarif"
OUTPUT_DIR_PATCHES="$OUTPUT_DIR/patches"

EXIT_CODE=0
(cd "$BUILD_WORKSPACE_DIRECTORY" && bazel run @rules_swiftnav//tools/lint:extract_lint_results -- \
  --build-event-json-file=$buildevents --bazel-output-path="$BUILD_WORKSPACE_DIRECTORY" \
  --output-merged-sarif-file="$OUTPUT_DIR_MERGED_SARIF" \
  --output-patch-folder="$OUTPUT_DIR_PATCHES" \
  --exit-code=1) || EXIT_CODE=$?

if [[ "$APPLY_PATCHES" == true ]]; then
    for patch in "$OUTPUT_DIR_PATCHES"/*.patch; do
        if [[ -f "$patch" ]]; then
            (cd "$BUILD_WORKSPACE_DIRECTORY" && patch -p1 <"$patch")
        fi
    done
fi

exit $EXIT_CODE
