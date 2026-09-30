#!/usr/bin/env bash
#
# Bazelisk wrapper: forwards all arguments to the real Bazel binary and
# refreshes compile_commands.json in the background after build-like commands.
# Copy to tools/bazel in the workspace root, see
# @rules_swiftnav//compile_commands:compile_commands.md.
# Bypass with BAZELISK_SKIP_WRAPPER=1.

set -uo pipefail

"${BAZEL_REAL:?BAZEL_REAL not set, tools/bazel must be run via bazel or bazelisk}" "$@"
exit_code=$?

if [[ -n "${CI:-}" || -n "${BCC_REFRESH:-}" ]]; then
    exit "${exit_code}"
fi

# Startup options precede the command and always use the --flag=value form.
command=""
for arg in "$@"; do
    if [[ "${arg}" != -* ]]; then
        command="${arg}"
        break
    fi
done

# The refresh runs detached with its output discarded. A failure is recorded in
# .cache/compile_commands.error, which the next successful refresh removes.
refresh() {
    local workspace error_file output status
    workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    error_file="${workspace}/.cache/compile_commands.error"
    output="$(BCC_REFRESH=1 "${BAZEL_REAL}" run --noshow_progress --ui_event_filters=-info \
        @rules_swiftnav//compile_commands:refresh -- --background 2>&1)"
    status=$?
    if [[ "${status}" -eq 0 ]]; then
        rm -f "${error_file}"
    else
        mkdir -p "${workspace}/.cache"
        printf 'background refresh failed with exit code %s at %s, see also .cache/compile_commands.log\n%s\n' \
            "${status}" "$(date)" "${output}" >"${error_file}"
    fi
}

case "${command}" in
    build | test | run)
        (
            trap '' HUP
            refresh
        ) </dev/null >/dev/null 2>&1 &
        ;;
esac

exit "${exit_code}"
