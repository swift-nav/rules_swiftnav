# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.

"""Module extension that fetches hermetic bazel_compile_commands binaries from upstream GitHub releases."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

_BCC_VERSION = "0.22.4"
_BCC_RELEASE = "bazel-compile-commands-v" + _BCC_VERSION
_BASE_URL = "https://github.com/kiron1/bazel-compile-commands/releases/download/" + _BCC_RELEASE
_BUILD_FILE_CONTENT = """\
load("@bazel_skylib//rules:native_binary.bzl", "native_binary")

package(default_visibility = ["//visibility:public"])

native_binary(
    name = "bcc_bin",
    src = "bin/bazel-compile-commands",
    out = "bazel-compile-commands",
)
"""

_BCC_ARCHIVES = {
    "bcc_linux_x86_64": struct(
        asset = "bazel-compile-commands_{v}-linux_amd64.zip".format(v = _BCC_VERSION),
        strip_prefix = "usr",
        sha256 = "bb162adaefb282a9e4f0f399fe6223d1d2fe3740518148c1ca8f6f81db4003f6",
    ),
    "bcc_macos_arm64": struct(
        asset = "bazel-compile-commands_{v}-macos_universal.zip".format(v = _BCC_VERSION),
        strip_prefix = "usr",
        sha256 = "6183cbaec5d9667e4def8590e4558a4e8eb106da34e2cd8a16733f8becf1ce4e",
    ),
}

def _bcc_extension_impl(_ctx):
    for repo_name, spec in _BCC_ARCHIVES.items():
        http_archive(
            name = repo_name,
            urls = ["{base}/{asset}".format(base = _BASE_URL, asset = spec.asset)],
            sha256 = spec.sha256,
            strip_prefix = spec.strip_prefix,
            build_file_content = _BUILD_FILE_CONTENT,
        )

bcc_extension = module_extension(implementation = _bcc_extension_impl)
