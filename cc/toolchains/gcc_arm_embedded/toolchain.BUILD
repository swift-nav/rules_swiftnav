package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/arm-none-eabi-cpp",
        "bin/arm-none-eabi-g++",
        "bin/arm-none-eabi-gcc",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/arm-none-eabi-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "lib/gcc/arm-none-eabi/10.3.1/include/**",
        "lib/gcc/arm-none-eabi/10.3.1/include-fixed/**",
        "arm-none-eabi/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "arm-none-eabi/bin/**",
    ]) + [
        "lib/gcc/arm-none-eabi/10.3.1/cc1",
        "lib/gcc/arm-none-eabi/10.3.1/cc1plus",
    ],
)

filegroup(
    name = "lib",
    srcs = glob([
        "arm-none-eabi/**/lib*.a",
        "lib/**/lib*.a",
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/arm-none-eabi-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/arm-none-eabi-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/arm-none-eabi-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/arm-none-eabi-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/arm-none-eabi-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/arm-none-eabi-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/arm-none-eabi-strip"],
)
