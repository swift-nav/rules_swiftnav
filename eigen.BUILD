load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

package(
    default_visibility = ["//visibility:public"],
)

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "eigen",
    cache_entries = {
        "CMAKE_C_FLAGS": "-fPIC",
    },
    defines = [
        "EIGEN_MPL_ONLY",
        "EIGEN_NO_DEBUG",
    ],
    includes = ["eigen3"],
    lib_source = ":srcs",
    out_headers_only = True,
    visibility = ["//visibility:public"],
)
