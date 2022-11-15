package(
    default_visibility = ["//visibility:public"],
)

cc_library(
    name = "rapidcheck",
    srcs = glob(["src/**"]),
    hdrs = glob(["include/**"] + ["extras/**"]),
    includes = [
        "extras/gtest/include",
        "include",
    ],
)
