#!/usr/bin/env bash
#
# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# Bazelisk wrapper: forwards all arguments to the real Bazel binary and
# refreshes compile_commands.json in the background after build-like commands.
# Copy to tools/bazel in the workspace root, see
# @rules_swiftnav//tools/compile_commands:README.md.
# Bypass with BAZELISK_SKIP_WRAPPER=1.

set -uo pipefail

"${BAZEL_REAL:?BAZEL_REAL not set, tools/bazel must be run via bazel or bazelisk}" "$@"
exit_code=$?

if [[ -n "${CI:-}" || -n "${BCC_REFRESH:-}" ]]; then
    exit "${exit_code}"
fi

# Startup options in the --flag=value form precede the command. The space form
# misdetects the command, which at worst skips the refresh.
command=""
command_flags=0
for arg in "$@"; do
    if [[ -z "${command}" ]]; then
        if [[ "${arg}" != -* ]]; then
            command="${arg}"
        fi
    elif [[ "${arg}" == "--" ]]; then
        break
    elif [[ "${arg}" == -* ]]; then
        command_flags=1
    fi
done

# The refresh uses default flags. After a build with command line flags it
# would discard the analysis cache of that build.
if [[ "${command_flags}" -eq 1 ]]; then
    exit "${exit_code}"
fi

case "${command}" in
    build | test | run)
        BCC_REFRESH=1 nohup "${BAZEL_REAL}" run --noshow_progress --ui_event_filters=-info \
            @rules_swiftnav//tools/compile_commands:refresh -- --background </dev/null >/dev/null 2>&1 &
        ;;
esac

exit "${exit_code}"
