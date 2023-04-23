package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/arm-linux-musleabifh-cpp",
        "bin/arm-linux-musleabifh-g++",
        "bin/arm-linux-musleabifh-gcc",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/arm-linux-musleabifh-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "lib/gcc/arm-linux-musleabifh/11.2.0/include/**",
        "lib/gcc/arm-linux-musleabifh/11.2.0/include-fixed/**",
        "arm-linux-musleabifh/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "arm-linux-musleabifh/bin/**",
    ]) + [
        "libexec/gcc/arm-linux-musleabifh/11.2.0/cc1",
        "libexec/gcc/arm-linux-musleabifh/11.2.0/cc1plus",
    ],
)

filegroup(
    name = "lib",
    srcs = glob([
        "arm-linux-musleabifh/**/lib*.a",
        "lib/**/lib*.a",
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/arm-linux-musleabifh-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/arm-linux-musleabifh-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/arm-linux-musleabifh-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/arm-linux-musleabifh-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/arm-linux-musleabifh-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/arm-linux-musleabifh-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/arm-linux-musleabifh-strip"],
)
