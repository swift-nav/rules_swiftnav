package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/arm-linux-musleabihf-cpp",
        "bin/arm-linux-musleabihf-g++",
        "bin/arm-linux-musleabihf-gcc",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/arm-linux-musleabihf-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "lib/gcc/arm-linux-musleabihf/11.2.0/include/**",
        "lib/gcc/arm-linux-musleabihf/11.2.0/include-fixed/**",
        "arm-linux-musleabihf/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "arm-linux-musleabihf/bin/**",
    ]) + [
        "libexec/gcc/arm-linux-musleabihf/11.2.0/cc1",
        "libexec/gcc/arm-linux-musleabihf/11.2.0/cc1plus",
        "libexec/gcc/arm-linux-musleabihf/11.2.0/liblto_plugin.so",
    ],
)

filegroup(
    name = "lib",
    srcs = glob([
        "arm-linux-musleabihf/lib/**",
        "arm-linux-musleabihf/**/lib*.a", # ?
        "lib/gcc/arm-linux-musleabihf/11.2.0/**",
        "lib/**/lib*.a", # ?
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/arm-linux-musleabihf-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/arm-linux-musleabihf-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/arm-linux-musleabihf-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/arm-linux-musleabihf-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/arm-linux-musleabihf-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/arm-linux-musleabihf-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/arm-linux-musleabihf-strip"],
)
