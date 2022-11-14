package(
    default_visibility = ["//visibility:public"],
)

yaml_cpp_defines = select({
    # On Windows, ensure static linking is used.
    "@platforms//os:windows": [
        "YAML_CPP_STATIC_DEFINE",
        "YAML_CPP_NO_CONTRIB",
    ],
    "//conditions:default": [],
})

cc_library(
    name = "yaml-cpp_internal",
    hdrs = glob(["src/**/*.h"]),
    strip_include_prefix = "src",
    visibility = ["//:__subpackages__"],
)

cc_library(
    name = "yaml-cpp",
    srcs = glob([
        "src/**/*.cpp",
        "src/**/*.h",
    ]),
    hdrs = glob(["include/**/*.h"]),
    defines = yaml_cpp_defines,
    includes = ["include"],
    visibility = ["//visibility:public"],
)
