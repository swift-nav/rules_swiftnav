package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/aarch64-linux-gnu-cpp",
        "bin/aarch64-linux-gnu-g++",
        "bin/aarch64-linux-gnu-gcc",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/aarch64-linux-gnu-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "lib/gcc/aarch64-linux-gnu/8.3.0/include/**",
        "lib/gcc/aarch64-linux-gnu/8.3.0/include-fixed/**",
        "aarch64-linux-gnu/include/**",
        "aarch64-linux-gnu/libc/usr/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "aarch64-linux-gnu/bin/**",
    ]) + [
        "libexec/gcc/aarch64-linux-gnu/8.3.0/cc1",
        "libexec/gcc/aarch64-linux-gnu/8.3.0/cc1plus",
    ],
)

filegroup(
    name = "lib",
    srcs = glob([
        "aarch64-linux-gnu/**/lib*.a",
        "lib/**/lib*.a",
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/aarch64-linux-gnu-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/aarch64-linux-gnu-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/aarch64-linux-gnu-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/aarch64-linux-gnu-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/aarch64-linux-gnu-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/aarch64-linux-gnu-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/aarch64-linux-gnu-strip"],
)
