# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Keep a repo's .clang-tidy in sync with the centralized one in rules_swiftnav."""

load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

_REFERENCE = "@rules_swiftnav//clang_tidy:clang_tidy_config"

def clang_tidy_config(name = "clang_tidy_config", config = "//:.clang-tidy", **kwargs):
    """Keeps `config` in sync with the .clang-tidy shipped by rules_swiftnav.

    Creates `<name>.update_test`, which fails if the two files differ, and
    `<name>.update`, which copies the centralized file over `config`.

    Args:
        name: Base target name.
        config: Label of the repo-local .clang-tidy, either an exported source
            file or a filegroup wrapping it.
        **kwargs: Passed to the test target.
    """
    update = "{}.update".format(name)
    script = "{}_update.sh".format(name)

    diff_test(
        name = "{}_test".format(update),
        file1 = config,
        file2 = _REFERENCE,
        failure_message = "{} is out of sync with {}. Run 'bazel run //{}:{}'.".format(
            config,
            _REFERENCE,
            native.package_name(),
            update,
        ),
        **kwargs
    )

    write_file(
        name = "{}_gen".format(update),
        out = script,
        content = [
            "#!/usr/bin/env bash",
            "set -o errexit",
            # bazel run executes from the runfiles tree, so $1 is a rootpath.
            'cp -f "$1" "$BUILD_WORKSPACE_DIRECTORY/$2"',
        ],
        is_executable = True,
    )

    sh_binary(
        name = update,
        srcs = [script],
        args = ["$(rootpath {})".format(_REFERENCE), "$(rootpath {})".format(config)],
        data = [_REFERENCE, config],
        tags = ["manual"],
    )
