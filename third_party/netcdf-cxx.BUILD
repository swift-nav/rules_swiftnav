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
    lib_source = ":srcs",
    out_shared_libs = ["libnetcdf-cxx4.so.1.1.0"],
    visibility = ["//visibility:public"],
)
