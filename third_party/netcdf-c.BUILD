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
        "BUILD_SHARED_LIBS": "OFF",
        "CMAKE_BUILD_TYPE": "Release",
        "ENABLE_DAP": "OFF",
        "ENABLE_EXAMPLES": "OFF",
        "ENABLE_PNETCDF": "OFF",
        "ENABLE_TESTS": "OFF",
        "ENABLE_NCZARR": "OFF",
        "USE_SZIP": "OFF",
    },
    copts = ["-fPIC"],
    lib_source = ":allsrcs",
    out_static_libs = ["libnetcdf.a"],
    visibility = ["//visibility:public"],
    deps = [
        "@hdf5",
    ],
)
