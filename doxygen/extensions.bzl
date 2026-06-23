# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.

"""Module extension that fetches hermetic Doxygen binaries from upstream GitHub releases."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

_DOXYGEN_VERSION = "1.17.0"
_DOXYGEN_RELEASE = "Release_1_17_0"
_BASE_URL = "https://github.com/doxygen/doxygen/releases/download/" + _DOXYGEN_RELEASE

_DOXYGEN_ARCHIVES = {
    "doxygen_linux_x86_64": struct(
        asset = "doxygen-{v}.linux.bin.tar.gz".format(v = _DOXYGEN_VERSION),
        strip_prefix = "doxygen-{v}".format(v = _DOXYGEN_VERSION),
        build_file = "@rules_swiftnav//doxygen:doxygen_linux.BUILD",
        sha256 = "75419ef4f446fc1c24ef12514b574e66e898ee6f527c6ae2ad84f91a905823c2",
    ),
    "doxygen_macos_arm64": struct(
        asset = "doxygen-{v}-mac-arm.zip".format(v = _DOXYGEN_VERSION),
        strip_prefix = "doxygen-{v}".format(v = _DOXYGEN_VERSION),
        build_file = "@rules_swiftnav//doxygen:doxygen_macos.BUILD",
        sha256 = "e05a7f647f894d2d82ef26a1d231cda079d2d1d85cf1e1c6fd8072430d80d614",
    ),
}

def _doxygen_extension_impl(_ctx):
    for repo_name, spec in _DOXYGEN_ARCHIVES.items():
        http_archive(
            name = repo_name,
            urls = ["{base}/{asset}".format(base = _BASE_URL, asset = spec.asset)],
            sha256 = spec.sha256,
            strip_prefix = spec.strip_prefix,
            build_file = spec.build_file,
        )

doxygen_extension = module_extension(implementation = _doxygen_extension_impl)
