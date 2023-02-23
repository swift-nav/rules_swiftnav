# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@bazel_tools//tools/cpp:unix_cc_toolchain_config.bzl",
     unix_cc_toolchain_config = "cc_toolchain_config"
)

def cc_toolchain_config(name):
    # These variables are passed directly through to unix_cc_toolchain_config 
    # below. As far as I can tell they are just metadata that doesn't affect 
    # the build.
    host_system_name = "linux-x86_64"
    toolchain_identifier = "clang-x86_64-linux"
    target_cpu = "k8"
    target_libc = "glibc_unknown"
    compiler = "clang"
    abi_version = "clang"
    abi_libc_version = "glibc_unknown"

    cxx_builtin_include_directories = [
        "/include",
        "/usr/include",
        "/usr/local/include",
    ]

    tool_paths = {
        "ar": "wrappers/llvm-ar",
        "cpp": "wrappers/clang-cpp",
        "gcc": "wrappers/clang",
        "gcov": "wrappers/llvm-profdata",
        "llvm-cov": "wrappers/llvm-cov",
        "llvm-profdata": "wrappers/llvm-profdata",
        "ld": "wrappers/ld.ldd",
        "nm": "wrappers/llvm-nm",
        "objcopy": "wrappers/llvm-objcopy",
        "objdump": "wrappers/llvm-objdump",
        "strip": "wrappers/llvm-strip",
    }

    target_system_name = "x86_64-unknown-linux-gnu"

    # Default compiler flags:
    compile_flags = [
        "--target=" + target_system_name,
        # Security
        "-U_FORTIFY_SOURCE",  # https://github.com/google/sanitizers/issues/247
        "-fstack-protector",
        "-fno-omit-frame-pointer",
        # Diagnostics
        "-fcolor-diagnostics",
        "-Wall",
        "-Wthread-safety",
        "-Wself-assign",
    ]

    # -fstandalone-debug disables options that optimize
    # the size of the debug info.
    # https://clang.llvm.org/docs/UsersManual.html#cmdoption-fstandalone-debug
    dbg_compile_flags = ["-g", "-fstandalong-debug"]

    opt_compile_flags = [
        # No debug symbols.
        "-g0",

        # Aggressive optimizations, can increase binary size.
        "-O3",

        # Security hardening on by default.
        "-D_FORTIFY_SOURCE=1",

        # Removal of unused code and data at link time (can this increase
        # binary size in some cases?).
        "-ffunction-sections",
        "-fdata-sections",
    ]

    cxx_flags = [
        # The whole codebase should build with c++14
        "-std=c++14",
        # Use bundled libc++ for hermeticity
        "-stdlib=libc++",
    ]

    link_flags = [
        "--target=" + target_system_name,
        "-lm",
        "-no-canonical-prefixes",
        # Below this line, assumes libc++ & lld
        "-l:libc++.a",
        "-l:libc++abi.a",
        "-l:libunwind.a",
        # Compiler runtime features.
        "-rtlib=compiler-rt",
        # To support libunwind
        # It's ok to assume posix when using this toolchain
        "-lpthread",
        "-ldl",
    ]

    # linux/lld only!
    link_flags.extend([
        "-fuse-ld=lld",
        "-Wl,--build-id=md5",
        "-Wl,--hash-style=gnu",
        "-Wl,-z,relro,-z,now",
    ])

    # Similar to link_flags, but placed later in the command line such that
    # unused symbols are not stripped.
    link_libs = []

    # linux/lld only
    opt_link_flags = ["-Wl,--gc-sections"]

    # Unfiltered compiler flags; these are placed at the end of the command
    # line, so take precendence over any user supplied flags through --copts or
    # such.
    unfiltered_compile_flags = [
        # Do not resolve our symlinked resource prefixes to real paths.
        "-no-canonical-prefixes",
        # Reproducibility
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
        # Grailbio uses this but in not sure it's necessary, given clang seems to respect PWD.
        # Will need to validate with some testing.
        #"-fdebug-prefix-map={}=__bazel_toolchain_llvm_repo__/".format(toolchain_path_prefix),
    ]


    # Coverage flags:
    coverage_compile_flags = ["-fprofile-instr-generate", "-fcoverage-mapping"]
    coverage_link_flags = ["-fprofile-instr-generate"]

    # true if using lld
    supports_start_end_lib = True

    unix_cc_toolchain_config(
        name = name,
        cpu = target_cpu,
        compiler = compiler,
        toolchain_identifier = toolchain_identifier,
        host_system_name = host_system_name,
        target_system_name = target_system_name,
        target_libc = target_libc,
        abi_version = abi_version,
        abi_libc_version = abi_libc_version,
        cxx_builtin_include_directories = cxx_builtin_include_directories,
        tool_paths = tool_paths,
        compile_flags = compile_flags,
        dbg_compile_flags = dbg_compile_flags,
        opt_compile_flags = opt_compile_flags,
        cxx_flags = cxx_flags,
        link_flags = link_flags,
        link_libs = link_libs,
        opt_link_flags = opt_link_flags,
        unfiltered_compile_flags = unfiltered_compile_flags,
        coverage_compile_flags = coverage_compile_flags,
        coverage_link_flags = coverage_link_flags,
        supports_start_end_lib = supports_start_end_lib,
    )
