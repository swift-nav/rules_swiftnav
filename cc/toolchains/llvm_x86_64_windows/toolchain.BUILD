package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/x86_64-w64-mingw32uwp-c++",
        "bin/x86_64-w64-mingw32uwp-g++",
        "bin/x86_64-w64-mingw32uwp-gcc",
    ],
)

filegroup(
    name = "clang",
    srcs = [
        "bin/clang-cpp",
        "bin/x86_64-w64-mingw32uwp-clang",
        "bin/x86_64-w64-mingw32uwp-clang++",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/x86_64-w64-mingw32uwp-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "x86_64-w64-mingw32/include/**",
        "lib/clang/*/include/**",
        "generic-w64-mingw32/include/c++/v1/*",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "x86_64-w64-mingw32/**",
    ]),
)

filegroup(
    name = "lib",
    srcs = glob([
        "lib/**/lib*.a",
        "lib/clang/*/lib/**/*.a",
        "x86_64-w64-mingw32/lib/*.a",
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/x86_64-w64-mingw32uwp-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/x86_64-w64-mingw32uwp-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/x86_64-w64-mingw32uwp-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/x86_64-w64-mingw32uwp-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/x86_64-w64-mingw32uwp-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/x86_64-w64-mingw32uwp-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/x86_64-w64-mingw32uwp-strip"],
)
