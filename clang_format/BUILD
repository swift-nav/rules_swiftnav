load(":choose_clang_format.bzl", "choose_clang_format")

choose_clang_format(
    name = "clang_format_bin",
    visibility = ["//visibility:public"],
)

filegroup(
    name = "_clang_format_bin",
    srcs = [":clang_format_bin"],
)

sh_binary(
    name = "clang_format",
    srcs = [
        "run_clang_format.sh",
    ],
    args = [
        "format_all",
        "$(location :_clang_format_bin)",
    ],
    data = [
        ":_clang_format_bin",
        "//:clang_format_config",
    ],
    visibility = ["//visibility:public"],
)
