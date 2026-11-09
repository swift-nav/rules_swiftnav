# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Tools to maintain the lockfile that the `s3_data` module extension reads."""

load("@rules_python//python:py_binary.bzl", "py_binary")

def s3_data_lockfile(name, lockfile, bucket, prefix = "sha256", endpoint_url = None):
    """Creates `<name>.upload` and `<name>.fetch` for `lockfile`.

    `bazel run :<name>.upload -- <files>` uploads files to
    `s3://<bucket>/<prefix>/<sha256>` and records them in `lockfile`.
    `bazel run :<name>.fetch -- [<files or dirs>]` downloads lockfile entries
    into the workspace for use outside Bazel. Both use the `aws` CLI and the
    caller's AWS credentials.

    Args:
        name: Base target name.
        lockfile: Workspace-relative path of the JSON lockfile, e.g. "data.lock.json".
        bucket: S3 bucket holding the objects.
        prefix: Key prefix; objects live at `<prefix>/<sha256>`.
        endpoint_url: Optional `--endpoint-url` for the aws CLI.
    """
    args = ["--bucket", bucket, "--prefix", prefix, "--lockfile", lockfile]
    if endpoint_url:
        args += ["--endpoint-url", endpoint_url]

    for command in ["upload", "fetch"]:
        py_binary(
            name = "{}.{}".format(name, command),
            main_module = "s3_data.s3_data",
            args = args + [command],
            tags = ["manual"],
            deps = [Label("//s3_data:s3_data_lib")],
        )
