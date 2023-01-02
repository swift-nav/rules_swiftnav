"""
netcdf-cxx@4.3.1
"""

load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "netcdf-cxx",
    cache_entries = {
        "BUILD_SHARED_LIBS": "OFF",
        "NCXX_ENABLE_TESTS": "OFF",
    },
    lib_source = ":srcs",
    out_static_libs = ["libnetcdf-cxx4.a"],
    visibility = ["//visibility:public"],
    deps = ["@netcdf-c"],
)
