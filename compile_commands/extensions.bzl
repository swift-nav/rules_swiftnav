# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.

"""Module extension that fetches prebuilt bazel-compile-commands (bcc) binaries from upstream GitHub releases."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

_BCC_VERSION = "0.22.4"
_BASE_URL = "https://github.com/kiron1/bazel-compile-commands/releases/download/bazel-compile-commands-v" + _BCC_VERSION

_BCC_BUILD_FILE_CONTENT = 'exports_files(["usr/bin/bazel-compile-commands"])'

_BCC_ARCHIVES = {
    "bcc_linux_amd64": struct(
        platform = "linux_amd64",
        integrity = "sha256-uxYq2u+ygqnk8POZ/mIj0dL+N0BRgUjByo9vgdtAA/Y=",
    ),
    "bcc_linux_arm64": struct(
        platform = "linux_arm64",
        integrity = "sha256-wa1aWhx6r3nY7+ViAe3gSxgLQDHuRMra/aE3O3UClJg=",
    ),
    "bcc_macos_universal": struct(
        platform = "macos_universal",
        integrity = "sha256-YYPLrsXZZn5N74WQ5FWKTo6xBto04s2KFnM/i+zxzk4=",
    ),
}

def _bcc_extension_impl(_ctx):
    for repo_name, spec in _BCC_ARCHIVES.items():
        http_archive(
            name = repo_name,
            urls = ["{base}/bazel-compile-commands_{version}-{platform}.zip".format(
                base = _BASE_URL,
                version = _BCC_VERSION,
                platform = spec.platform,
            )],
            integrity = spec.integrity,
            build_file_content = _BCC_BUILD_FILE_CONTENT,
        )

bcc_extension = module_extension(implementation = _bcc_extension_impl)
