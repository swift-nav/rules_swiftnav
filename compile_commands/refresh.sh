#!/usr/bin/env bash
#
# Regenerates compile_commands.json in the root of the calling workspace if the
# build structure changed since the last successful run.
#
# Usage: bazel run @rules_swiftnav//compile_commands:refresh -- [--force] [--background]
#   --force       regenerate even if the stamp is up to date; waits up to
#                 BCC_LOCK_TIMEOUT seconds (default 600) for a running refresh
#   --background  write generator output to .cache/compile_commands.log
#   --bcc=PATH    bazel-compile-commands binary, set by the refresh target

set -euo pipefail

usage() {
    echo "usage: bazel run @rules_swiftnav//compile_commands:refresh -- [--force] [--background]" >&2
    exit 2
}

force=0
background=0
bcc=""
for arg in "$@"; do
    case "${arg}" in
        --force) force=1 ;;
        --background) background=1 ;;
        --bcc=*) bcc="${arg#--bcc=}" ;;
        *) usage ;;
    esac
done

if [[ -z "${BUILD_WORKSPACE_DIRECTORY:-}" || -z "${bcc}" ]]; then
    usage
fi

# Runfiles paths are relative to the initial working directory.
bcc="$(cd "$(dirname "${bcc}")" && pwd)/$(basename "${bcc}")"

workspace="${BUILD_WORKSPACE_DIRECTORY}"
cd "${workspace}"

cache_dir="${workspace}/.cache"
stamp="${cache_dir}/compile_commands.stamp"
lock_file="${cache_dir}/compile_commands.lock"
lock_timeout="${BCC_LOCK_TIMEOUT:-600}"
log_file="${cache_dir}/compile_commands.log"
# Written by the tools/bazel wrapper when a background refresh fails.
error_file="${cache_dir}/compile_commands.error"
tmp_output="${cache_dir}/compile_commands.json.tmp.$$"
output="${workspace}/compile_commands.json"

structure_pathspecs=(
    ':(glob)**/BUILD'
    ':(glob)**/BUILD.bazel'
    ':(glob)**/*.bzl'
    ':(glob)**/*.bazelrc'
    ':(glob)toolchains/**'
    '.bazelrc'
    '.bazeliskrc'
    '.bazelccrc'
    'MODULE.bazel'
    'MODULE.bazel.lock'
)

source_pathspecs=(
    ':(glob)**/*.c'
    ':(glob)**/*.cc'
    ':(glob)**/*.cpp'
    ':(glob)**/*.cxx'
    ':(glob)**/*.h'
    ':(glob)**/*.hh'
    ':(glob)**/*.hpp'
    ':(glob)**/*.hxx'
    ':(glob)**/*.inc'
    ':(glob)**/*.ipp'
)

log() {
    echo "compile_commands: $*" >&2
}

# The lock is a symlink whose target is the owner pid: symlink(2) is atomic and
# creates lock and owner in one step, so a lock never exists without an owner.
# Unlike flock it is available on macOS out of the box.
lock_owner() {
    readlink "${lock_file}" 2>/dev/null || true
}

holds_lock() {
    [[ "$(lock_owner)" == "$$" ]]
}

try_lock() {
    # ln into an existing directory would create a link inside it.
    if [[ -e "${lock_file}" || -L "${lock_file}" ]]; then
        return 1
    fi
    ln -s "$$" "${lock_file}" 2>/dev/null && holds_lock
}

# Anything at the lock path without a live numeric owner is stale, including
# directory locks left behind by older versions of this script.
reclaim_stale_lock() {
    if [[ ! -e "${lock_file}" && ! -L "${lock_file}" ]]; then
        return 0
    fi
    local owner
    owner="$(lock_owner)"
    if [[ "${owner}" =~ ^[0-9]+$ ]] && kill -0 "${owner}" 2>/dev/null; then
        return 1
    fi
    # rename is atomic, so only one of several reclaimers gets the stale entry.
    local grave="${lock_file}.stale.$$"
    mv "${lock_file}" "${grave}" 2>/dev/null || return 1
    local grabbed
    grabbed="$(readlink "${grave}" 2>/dev/null || true)"
    if [[ "${grabbed}" != "${owner}" ]]; then
        # A fresh lock replaced the stale one before the rename: hand it back.
        ln -s "${grabbed}" "${lock_file}" 2>/dev/null || true
        rm -rf "${grave}"
        return 1
    fi
    log "removing stale lock${owner:+ of pid ${owner}}"
    rm -rf "${grave}"
}

release_lock() {
    rm -f "${tmp_output}" "${tmp_output}.bak"
    if holds_lock; then
        rm -f "${lock_file}"
    fi
}

acquire_lock() {
    mkdir -p "${cache_dir}"
    if try_lock || { reclaim_stale_lock && try_lock; }; then
        trap release_lock EXIT
        return 0
    fi
    return 1
}

list_files() {
    git ls-files -z --cached --others --exclude-standard --deduplicate -- "$@"
}

# Build structure only: BUILD/config file contents plus the set of C/C++ file
# names. Source file contents do not affect compile commands.
input_hash() {
    local structure_files
    structure_files="$(
        list_files "${structure_pathspecs[@]}" | sort -z | while IFS= read -r -d '' file; do
            if [[ -f "${file}" ]]; then printf '%s\n' "${file}"; fi
        done
        # Gitignored, hence not listed by git.
        if [[ -f .bazelrc.user ]]; then echo .bazelrc.user; fi
    )"
    {
        printf '%s\n' "${structure_files}"
        # --stdin-paths resolves relative paths against the git toplevel, which
        # differs from the workspace when the workspace is nested in the repo.
        printf '%s\n' "${structure_files}" | while IFS= read -r file; do
            printf '%s/%s\n' "${workspace}" "${file}"
        done | git hash-object --stdin-paths
        list_files "${source_pathspecs[@]}" | sort -z | tr '\0' '\n'
    } | git hash-object --stdin
}

if ! acquire_lock; then
    if [[ "${force}" -eq 0 ]]; then
        log "refresh already in progress"
        exit 0
    fi
    owner="$(lock_owner)"
    log "waiting for running refresh${owner:+ of pid ${owner}} to finish"
    waited=0
    until acquire_lock; do
        if ((waited >= lock_timeout)); then
            log "timed out after ${lock_timeout}s waiting for ${lock_file}"
            exit 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
fi

hash="$(input_hash)"
if [[ "${force}" -eq 0 && -f "${output}" && -f "${stamp}" && "$(cat "${stamp}")" == "${hash}" ]]; then
    rm -f "${error_file}"
    log "up to date"
    exit 0
fi

if [[ "${background}" -eq 1 ]]; then
    exec >"${log_file}" 2>&1
fi

log "regenerating ${output}"

# BCC_REFRESH keeps a tools/bazel wrapper from triggering another refresh when
# bcc calls bazel for `info` and `aquery`.
export BCC_REFRESH=1
bazel_command="${BAZEL_REAL:-bazel}"
bcc_args=(--output "${tmp_output}")
if [[ -n "${BAZEL_REAL:-}" ]]; then
    bcc_args+=(--bazel-command "${BAZEL_REAL}")
fi

fail() {
    rm -f "${tmp_output}"
    log "$*, keeping previous ${output}"
    exit 1
}

"${bcc}" "${bcc_args[@]}" || fail "generation failed"

execution_root="$("${bazel_command}" info execution_root 2>/dev/null)" || fail "bazel info failed"
output_base="$("${bazel_command}" info output_base 2>/dev/null)" || fail "bazel info failed"

# bcc emits paths relative to the execroot, whose external/ symlink forest only
# holds the repos of the last build. Resolving relative to the workspace with
# external/ pointing at the output base keeps all external headers reachable.
# `resolve` in .bazelccrc only rewrites the `file` entries, not the arguments.
ln -sfn "${output_base}/external" "${workspace}/external"
sed -i.bak "s|\"directory\":\"${execution_root}\"|\"directory\":\"${workspace}\"|g" "${tmp_output}" ||
    fail "rewriting directory failed"
rm -f "${tmp_output}.bak"

holds_lock || fail "lost ${lock_file} to pid $(lock_owner)"
mv -f "${tmp_output}" "${output}"
echo "${hash}" >"${stamp}"
rm -f "${error_file}"
log "done"
