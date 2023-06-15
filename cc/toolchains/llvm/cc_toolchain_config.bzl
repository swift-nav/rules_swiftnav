# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load(
    "@bazel_tools//tools/cpp:unix_cc_toolchain_config.bzl",
    unix_cc_toolchain_config = "cc_toolchain_config",
)
load("//cc/toolchains/llvm:target_triplets.bzl", "is_target_triplet")

def cc_toolchain_config(
        name,
        host_system_name,
        toolchain_identifier,
        toolchain_path_prefix,
        target_cpu,
        target_libc,
        compiler,
        abi_version,
        abi_libc_version,
        cxx_builtin_include_directories,
        tool_paths,
        target_system_name,
        builtin_sysroot = None,
        is_darwin = False):
    if not is_target_triplet(host_system_name):
        fail(host_system_name + " is not a target tripplet")

    if not is_target_triplet(target_system_name):
        fail(target_system_name + " is not a target tripplet")

    use_libstdcpp = builtin_sysroot != None and not is_darwin

    # Default compiler flags:
    compile_flags = [
        "--target=" + target_system_name,
        # Security
        "-U_FORTIFY_SOURCE",  # https://github.com/google/sanitizers/issues/247
        "-fstack-protector",
        "-fno-omit-frame-pointer",
        # Math
        # This controls whether the compiler allows contracting floating point operations.
        # It was flipped from off to on in clang-14.
        # For now we'd like to preserve the legacy behavior.
        # See [BUILD-666] for more details.
        "-ffp-contract=off",
        # Diagnostics
        "-fcolor-diagnostics",
        "-Wall",
        "-Wthread-safety",
        "-Wself-assign",
    ]

    # -fstandalone-debug disables options that optimize
    # the size of the debug info.
    # https://clang.llvm.org/docs/UsersManual.html#cmdoption-fstandalone-debug
    dbg_compile_flags = ["-g", "-fstandalone-debug"]

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
        # Use bundled libc++ for hermeticity if not cross compiling
    ] + ["-stdlib=libstdc++"] if use_libstdcpp else ["-stdlib=libc++"]

    link_flags = [
        "--target=" + target_system_name,
        "-lm",
        "-no-canonical-prefixes",
    ]

    # Similar to link_flags, but placed later in the command line such that
    # unused symbols are not stripped.
    link_libs = []

    if is_darwin:
        # Mach-O support in lld is experimental, so on mac
        # we use the system linker.
        use_lld = False
        link_flags.extend([
            "-headerpad_max_install_names",
            # This will issue a warning on macOS ventura; see:
            # https://github.com/python/cpython/issues/97524
            # https://developer.apple.com/forums/thread/719961
            "-undefined",
            "dynamic_lookup",
            "-Wl,-no_fixup_chains",
        ])
    else:
        use_lld = True
        link_flags.extend([
            "-fuse-ld=lld",
            "-Wl,--build-id=md5",
            "-Wl,--hash-style=gnu",
            "-Wl,-z,relro,-z,now",
        ])

    if use_lld:
        link_flags.extend([
            # To support libunwind
            # It's ok to assume posix when using this toolchain
            "-lpthread",
            "-ldl",
        ])

        if use_libstdcpp:
            link_flags.extend([
                # Use libstdc++ from the sysroot when cross compiling
                "-l:libstdc++.a",
            ])
        else:
            link_flags.extend([
                # Below this line, assumes libc++ & lld
                "-l:libc++.a",
                "-l:libc++abi.a",
                "-l:libunwind.a",
                # Compiler runtime features.
                "-rtlib=compiler-rt",
            ])
    else:
        # The comments below were copied directly from:
        # https://github.com/grailbio/bazel-toolchain/blob/795d76fd03e0b17c0961f0981a8512a00cba4fa2/toolchain/cc_toolchain_config.bzl#L202

        # The only known mechanism to static link libraries in ld64 is to
        # not have the corresponding .dylib files in the library search
        # path. The link time sandbox does not include the .dylib files, so
        # anything we pick up from the toolchain should be statically
        # linked. However, several system libraries on macOS dynamically
        # link libc++ and libc++abi, so static linking them becomes a problem.
        # We need to ensure that they are dynamic linked from the system
        # sysroot and not static linked from the toolchain, so explicitly
        # have the sysroot directory on the search path and then add the
        # toolchain directory back after we are done.
        link_flags.extend([
            "-L{}/usr/lib".format(builtin_sysroot),
            "-lc++",
            "-lc++abi",
        ])

        # Let's provide the path to the toolchain library directory
        # explicitly as part of the search path to make it easy for a user
        # to pick up something. This also makes the behavior consistent with
        # targets when a user explicitly depends on something like
        # libomp.dylib, which adds this directory to the search path, and would
        # (unintentionally) lead to static linking of libraries from the
        # toolchain.
        link_flags.extend([
            "-L{}/lib".format(toolchain_path_prefix),
        ])

    # linux/lld only
    opt_link_flags = ["-Wl,--gc-sections"] if not is_darwin else []

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

    supports_start_end_lib = use_lld

    # Calls https://github.com/bazelbuild/bazel/blob/master/tools/cpp/unix_cc_toolchain_config.bzl
    # Which defines the rule that actually sets up the cc toolchain.
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
        builtin_sysroot = builtin_sysroot,
    )
