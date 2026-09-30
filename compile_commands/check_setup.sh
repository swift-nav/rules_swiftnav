#!/usr/bin/env bash
#
# Verifies that the calling workspace is set up for automatic
# compile_commands.json generation, see compile_commands.md.
#
# Usage: bazel run @rules_swiftnav//compile_commands:check_setup
#   --wrapper=PATH  bazel_wrapper.sh of this rules_swiftnav version, set by
#                   the check_setup target

set -euo pipefail

usage() {
    echo "usage: bazel run @rules_swiftnav//compile_commands:check_setup" >&2
    exit 2
}

wrapper=""
for arg in "$@"; do
    case "${arg}" in
        --wrapper=*) wrapper="${arg#--wrapper=}" ;;
        *) usage ;;
    esac
done

if [[ -z "${BUILD_WORKSPACE_DIRECTORY:-}" || -z "${wrapper}" ]]; then
    usage
fi

# Runfiles paths are relative to the initial working directory.
wrapper="$(cd "$(dirname "${wrapper}")" && pwd)/$(basename "${wrapper}")"

cd "${BUILD_WORKSPACE_DIRECTORY}"

problems=0
problem() {
    echo "compile_commands: $*" >&2
    problems=$((problems + 1))
}

if [[ ! -f tools/bazel ]]; then
    problem "tools/bazel is missing, copy it from @rules_swiftnav//compile_commands:bazel_wrapper.sh"
else
    if ! cmp -s tools/bazel "${wrapper}"; then
        problem "tools/bazel differs from @rules_swiftnav//compile_commands:bazel_wrapper.sh, copy it again"
    fi
    if [[ ! -x tools/bazel ]]; then
        problem "tools/bazel is not executable, run: git update-index --chmod=+x tools/bazel"
    fi
fi

if [[ ! -f .bazelccrc ]]; then
    problem ".bazelccrc is missing, copy it from @rules_swiftnav//compile_commands:.bazelccrc"
fi

for entry in compile_commands.json external .cache/; do
    if ! git check-ignore --quiet --no-index "${entry}"; then
        problem "${entry} is not ignored by git, add /${entry} to .gitignore"
    fi
done

if ((problems > 0)); then
    exit 1
fi
echo "compile_commands: setup is up to date" >&2
