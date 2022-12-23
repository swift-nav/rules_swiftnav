"""
netcdf-c@4.9.0
"""

load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

filegroup(
    name = "allsrcs",
    srcs = glob(["**"]),
)

cmake(
    name = "netcdf-c",
    cache_entries = {
        "BUILD_SHARED_LIBS": "ON",
        "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_INSTALL_LIBDIR": "lib",
        "ENABLE_DAP": "OFF",
        "ENABLE_EXAMPLES": "OFF",
        "ENABLE_PNETCDF": "OFF",
        "ENABLE_TESTS": "OFF",
        "USE_SZIP": "OFF",
    },
    generate_args = ["-GNinja"],
    lib_source = ":allsrcs",
    out_shared_libs = ["libnetcdf.so"],
    visibility = ["//visibility:public"],
    deps = [
        "@hdf5",
    ],
)
