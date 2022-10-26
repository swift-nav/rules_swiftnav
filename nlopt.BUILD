load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

package(
    default_visibility = ["//visibility:public"],
)

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "nlopt",
    cache_entries = {
        "CMAKE_C_FLAGS": "-fPIC",
    },
    generate_args = ["-DBUILD_SHARED_LIBS=OFF"],
    lib_source = ":srcs",
    out_static_libs = ["libnlopt.a"],
    visibility = ["//visibility:public"],
)
