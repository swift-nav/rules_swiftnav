# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""An openssl build file based on the rules_foreign_cc examples:
https://github.com/bazelbuild/rules_foreign_cc/blob/0ed27c13b18f412e00e9122fc01327503d52579c/examples/third_party/openssl/BUILD.openssl.bazel

Note that the $(PERL) "make variable" (https://docs.bazel.build/versions/main/be/make-variables.html)
is populated by the perl toolchain provided by rules_perl.
"""

load("@rules_foreign_cc//foreign_cc:defs.bzl", "configure_make")

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

configure_make(
    name = "openssl",
    configure_command = "Configure",
    configure_in_place = True,
    configure_options = select(
        {
            "@bazel_tools//src/conditions:linux_x86_64": ["linux-x86_64"],
            "@bazel_tools//src/conditions:linux_aarch64": ["linux-aarch64"],
            "@bazel_tools//src/conditions:darwin_x86_64": ["darwin64-x86_64-cc"],
            "@rules_swiftnav//platforms:aarch64_darwin": ["darwin64-arm64-cc"],
        },
        no_match_error = "Currently only aarch64-darwin, x86_64-darwin, x86_64-linux, and aarch64-linux are supported.",
    ) + [
        "no-comp",
        "no-idea",
        "no-weak-ssl-ciphers",
    ],
    env = select({
        "@platforms//os:macos": {
            "ARFLAGS": "-o",  # libtool is the ar on mac and requires the -o flag
            "PERL": "$$EXT_BUILD_ROOT$$/$(PERL)",
        },
        "//conditions:default": {
            "PERL": "$$EXT_BUILD_ROOT$$/$(PERL)",
        },
    }),
    lib_name = "openssl",
    lib_source = ":srcs",
    out_shared_libs = select({
        "@platforms//os:macos": [
            "libssl.1.1.dylib",
            "libcrypto.1.1.dylib",
        ],
        "//conditions:default": [
            "libssl.so.1.1",
            "libcrypto.so.1.1",
        ],
    }),
    targets = [
        "build_programs",
        "install_sw",
    ],
    toolchains = ["@rules_perl//:current_toolchain"],
    visibility = ["//visibility:public"],
)
