load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

package(
    default_visibility = ["//visibility:public"],
)

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "rapidcheck",
    cache_entries = {
        "CMAKE_C_FLAGS": "-fPIC",
    },
    generate_args = [
        "-DRC_ENABLE_GTEST=ON",
    ],
    lib_source = ":srcs",
    # out_interface_libs = ["rapidcheck_gtest.lib"],
    # out_include_dir = "costam",
    out_static_libs = ["librapidcheck.a"],
    visibility = ["//visibility:public"],
)
