load(":choose_clang_format.bzl", "choose_clang_format")

filegroup(
    name = "clang_format_config_default",
    srcs = [".clang-format"],
)

label_flag(
    name = "clang_format_config",
    build_setting_default = ":clang_format_config_default",
    visibility = ["//visibility:public"],
)

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
        "$(location :clang_format_config)",
    ],
    data = [
        ":_clang_format_bin",
        ":clang_format_config",
    ],
    visibility = ["//visibility:public"],
)

exports_files(
    glob(["*.bzl"]) + ["run_clang_format.sh"] + [".clang-format"],
    visibility = ["//visibility:public"],
)
