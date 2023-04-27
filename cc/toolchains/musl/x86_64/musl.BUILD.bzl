package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/x86_64-linux-musl-cpp",
        "bin/x86_64-linux-musl-g++",
        "bin/x86_64-linux-musl-gcc",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/x86_64-linux-musl-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "lib/gcc/x86_64-linux-musl/11.2.0/include/**",
        "lib/gcc/x86_64-linux-musl/11.2.0/include-fixed/**",
        "x86_64-linux-musl/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "x86_64-linux-musl/bin/**",
    ]) + [
        "libexec/gcc/x86_64-linux-musl/11.2.0/cc1",
        "libexec/gcc/x86_64-linux-musl/11.2.0/cc1plus",
        "libexec/gcc/x86_64-linux-musl/11.2.0/liblto_plugin.so",
    ],
)

filegroup(
    name = "lib",
    srcs = glob([
        "x86_64-linux-musl/lib/**",
        "x86_64-linux-musl/**/lib*.a",  # ?
        "lib/gcc/x86_64-linux-musl/11.2.0/**",
        "lib/**/lib*.a",  # ?
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/x86_64-linux-musl-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/x86_64-linux-musl-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/x86_64-linux-musl-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/x86_64-linux-musl-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/x86_64-linux-musl-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/x86_64-linux-musl-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/x86_64-linux-musl-strip"],
)
