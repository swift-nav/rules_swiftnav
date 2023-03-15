# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Swift wrappers for native cc rules."""

load("//tools:stamp_file.bzl", "stamp_file")
load(":utils.bzl", "construct_local_include")
load(":copts.bzl", "DEFAULT_COPTS", "GCC6_COPTS")

# Name for a unit test
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

# Name for swift_cc_library
LIBRARY = "library"

# Name for swift_cc_binary
BINARY = "binary"

# Name for swift_cc_test_library
TEST_LIBRARY = "test_library"

# Name for swift_cc_test
TEST = "test"

# Name for test sources
TEST_SRCS = "test_srcs"

# Form the c standard string
def _c_standard(extensions = False, standard = 99):
    extensions = "gnu" if extensions else "c"
    return ["-std={}{}".format(extensions, standard)]

# Form the c++ standard string.
def _cxx_standard(default, override):
    return default if not override else "-std=c++{}".format(override)

# Options common to both c and c++ code
def _common_cc_opts(nocopts, pedantic = False):
    return select({
        Label("//cc/constraints:gcc-6"): [copt for copt in GCC6_COPTS if copt not in nocopts],
        "//conditions:default": [copt for copt in DEFAULT_COPTS if copt not in nocopts],
    }) + ["-pedantic"] if pedantic else []

# Options specific to c++ code (exceptions, rtti, etc..)
def _common_cxx_opts(exceptions = False, rtti = False, standard = None):
    return select({
        Label("//cc:_enable_exceptions"): ["-fexceptions"],
        "//conditions:default": ["-fno-exceptions" if not exceptions else "-fexceptions"],
    }) + select({
        Label("//cc:_enable_rtti"): ["-frtti"],
        "//conditions:default": ["-fno-rtti" if not rtti else "-frtti"],
    }) + select({
        Label("//cc:cxx17"): [_cxx_standard("-std=c++17", standard)],
        Label("//cc:cxx20"): [_cxx_standard("-std=c++20", standard)],
        Label("//cc:cxx23"): [_cxx_standard("-std=c++23", standard)],
        "//conditions:default": [_cxx_standard("-std=c++14", standard)],
    })

# Handle various nuances of local include paths
def _construct_local_includes(local_includes):
    return [construct_local_include(path) for path in local_includes]

# Some options like -Werror are set using toolchain features
# See: https://bazel.build/docs/cc-toolchain-config-reference#features
def _default_features():
    return select({
        # treat_warnings_as_errors passes the option -fatal-warnings
        # to the linker which ld on mac does not understand.
        "@platforms//os:macos": [],
        "//conditions:default": ["treat_warnings_as_errors"],
    })

# Disable building when --//:disable_tests=true or when building on windows
def _test_compatible_with():
    return select({
        Label("//cc:_disable_tests"): ["@platforms//:incompatible"],
        "@platforms//os:windows": ["@platforms//:incompatible"],
        "//conditions:default": [],
    })

def cc_stamped_library(name, out, template, hdrs, includes, defaults, visibility = None):
    """Creates a cc_library stamped with non-hermetic build metadata.

    Creates a cc_library from the input template with values of the form @VAL@
    substituted with values from the workspace status program. This typically
    includes version control information, timestamps, and other similiar
    data. The output file is only compiled into the final resulting binary.

    Currently only stable status variables are supported.

    See https://bazel.build/docs/user-manual#workspace-status for more.

    Args:
        name: The name of the target
        out: The expanded source file
        template: The input template
        hdrs: See https://bazel.build/reference/be/c-cpp#cc_library.hdrs
        includes: See https://bazel.build/reference/be/c-cpp#cc_library.includes
        defaults: Dict of default values when stamping is not enabled
        visibility: See https://bazel.build/reference/be/common-definitions#common.visibility
    """

    source_name = name + "_"

    stamp_file(name = source_name, out = out, defaults = defaults, template = template)

    swift_cc_library(
        name = name,
        hdrs = hdrs,
        includes = includes,
        linkstamp = source_name,
        visibility = visibility,
    )

def swift_c_library(**kwargs):
    """Wraps cc_library to enforce standards for a production c library.

    Primarily this consists of a default set of compiler options and
    language standards.

    Production targets (swift_cc*), are compiled with the -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_library

            The following additional attributes are supported:

            extensions: Bool to enable c extensions (-std=gnu).

            standard: Override the default c standard (99). Passed to compiler
            as -std={gnu/c}{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])  # pop because nocopts is a deprecated cc* attr.

    copts = _common_cc_opts(nocopts, pedantic = True)
    copts = local_includes + copts

    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", 99)

    c_standard = _c_standard(extensions, standard)

    kwargs["copts"] = copts + c_standard + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    kwargs["tags"] = [LIBRARY] + kwargs.get("tags", [])

    native.cc_library(**kwargs)

def swift_cc_library(**kwargs):
    """Wraps cc_library to enforce standards for a production c++ library.

    Primarily this consists of a default set of compiler options and
    language standards.

    Production targets (swift_cc*), are compiled with the -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_library

            The following additional attributes are supported:

            exceptions: Bool to enable building with exceptions.

            rtti: Bool to enable building with rtti.

            standard: Override the default c++ standard (14). Passed to compiler as
            -std=c++{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])  # pop because nocopts is a deprecated cc* attr.

    copts = _common_cc_opts(nocopts, pedantic = True)
    copts = local_includes + copts

    exceptions = kwargs.pop("exceptions", False)
    rtti = kwargs.pop("rtti", False)
    standard = kwargs.pop("standard", None)

    cxxopts = _common_cxx_opts(exceptions, rtti, standard)

    kwargs["copts"] = copts + cxxopts + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    kwargs["tags"] = [LIBRARY] + kwargs.get("tags", [])

    native.cc_library(**kwargs)

def swift_c_tool_library(**kwargs):
    """Wraps cc_library to enforce standards for a non-production c library.

    Primarily this consists of a default set of compiler options and
    language standards.

    Non-production targets (swift_cc_tool*), are compiled without the
    -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_library

            The following additional attributes are supported:

            extensions: Bool to enable c extensions (-std=gnu).

            standard: Override the default c standard (99). Passed to compiler
            as -std={gnu/c}{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])

    copts = _common_cc_opts(nocopts, pedantic = False)
    copts = local_includes + copts

    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", 99)

    c_standard = _c_standard(extensions, standard)

    kwargs["copts"] = copts + c_standard + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    native.cc_library(**kwargs)

def swift_cc_tool_library(**kwargs):
    """Wraps cc_library to enforce standards for a non-production c++ library.

    Primarily this consists of a default set of compiler options and
    language standards.

    Non-production targets (swift_cc_tool*), are compiled without the
    -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_library

            The following additional attributes are supported:

            exceptions: Bool to enable building with exceptions.

            rtti: Bool to enable building with rtti.

            standard: Override the default c++ standard (14). Passed to compiler as
            -std=c++{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])

    copts = _common_cc_opts(nocopts, pedantic = False)
    copts = local_includes + copts

    exceptions = kwargs.pop("exceptions", False)
    rtti = kwargs.pop("rtti", False)
    standard = kwargs.pop("standard", None)

    cxxopts = _common_cxx_opts(exceptions, rtti, standard)

    kwargs["copts"] = copts + cxxopts + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    native.cc_library(**kwargs)

def swift_c_binary(**kwargs):
    """Wraps cc_binary to enforce standards for a production c binary.

    Primarily this consists of a default set of compiler options and
    language standards.

    Production targets (swift_cc*), are compiled with the -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_binary

            The following additional attributes are supported:

            extensions: Bool to enable c extensions (-std=gnu).

            standard: Override the default c standard (99). Passed to compiler
            as -std={gnu/c}{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])

    copts = _common_cc_opts(nocopts, pedantic = True)
    copts = local_includes + copts

    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", 99)
    c_standard = _c_standard(extensions, standard)

    kwargs["copts"] = copts + c_standard + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    kwargs["tags"] = [BINARY] + kwargs.get("tags", [])

    native.cc_binary(**kwargs)

def swift_cc_binary(**kwargs):
    """Wraps cc_binary to enforce standards for a production c++ binary.

    Primarily this consists of a default set of compiler options and
    language standards.

    Production targets (swift_cc*), are compiled with the -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_binary

            The following additional attributes are supported:

            exceptions: Bool to enable building with exceptions.

            rtti: Bool to enable building with rtti.

            standard: Override the default c++ standard (14). Passed to compiler as
            -std=c++{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])

    copts = _common_cc_opts(nocopts, pedantic = True)
    copts = local_includes + copts

    exceptions = kwargs.pop("exceptions", False)
    rtti = kwargs.pop("rtti", False)
    standard = kwargs.pop("standard", None)

    cxxopts = _common_cxx_opts(exceptions, rtti, standard)

    kwargs["copts"] = copts + cxxopts + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    kwargs["tags"] = [BINARY] + kwargs.get("tags", [])

    native.cc_binary(**kwargs)

def swift_c_tool(**kwargs):
    """Wraps cc_binary to enforce standards for a non-production c binary.

    Primarily this consists of a default set of compiler options and
    language standards.

    Non-production targets (swift_cc_tool*), are compiled without the
    -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_binary

            The following additional attributes are supported:

            extensions: Bool to enable c extensions (-std=gnu).

            standard: Override the default c standard (99). Passed to compiler
            as -std={gnu/c}{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_cc_opts(nocopts, pedantic = False)

    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", 99)

    c_standard = _c_standard(extensions, standard)

    kwargs["copts"] = copts + c_standard + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    native.cc_binary(**kwargs)

def swift_cc_tool(**kwargs):
    """Wraps cc_binary to enforce standards for a non-production c++ binary.

    Primarily this consists of a default set of compiler options and
    language standards.

    Non-production targets (swift_cc_tool*), are compiled without the
    -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_binary

            The following additional attributes are supported:

            exceptions: Bool to enable building with exceptions.

            rtti: Bool to enable building with rtti.

            standard: Override the default c++ standard (14). Passed to compiler as
            -std=c++{standard}.

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_cc_opts(nocopts, pedantic = False)

    exceptions = kwargs.pop("exceptions", False)
    rtti = kwargs.pop("rtti", False)
    standard = kwargs.pop("standard", None)

    cxxopts = _common_cxx_opts(exceptions, rtti, standard)

    kwargs["copts"] = copts + cxxopts + kwargs.get("copts", [])

    kwargs["features"] = _default_features() + kwargs.get("features", [])

    native.cc_binary(**kwargs)

def swift_cc_test_library(**kwargs):
    """Wraps cc_library to enforce Swift test library conventions.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_test

            The following additional attributes are supported:

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.
    """

    _ = kwargs.pop("nocopts", [])  # To handle API compatibility.

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    kwargs["copts"] = local_includes + kwargs.get("copts", [])

    kwargs["tags"] = [TEST_LIBRARY] + kwargs.get("tags", [])

    kwargs["target_compatible_with"] = kwargs.get("target_compatible_with", []) + _test_compatible_with()

    native.cc_library(**kwargs)

def swift_cc_test(name, type, **kwargs):
    """Wraps cc_test to enforce Swift testing conventions.

    This rule creates a test target along with a target that contains the sources
    of the test. The name of the sources is created with the '_src' suffix.

    Args:
        name: A unique name for this rule.
        type: Specifies whether the test is a unit or integration test.

            These are passed to cc_test as tags which enables running
            these test types seperately: `bazel test --test_tag_filters=unit //...`

        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_test

            The following additional attributes are supported:

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.
    """

    _ = kwargs.pop("nocopts", [])  # To handle API compatibility.

    srcs_name = name + "_srcs"
    srcs = kwargs.get("srcs", [])

    native.filegroup(
        name = srcs_name,
        srcs = srcs,
        visibility = ["//visibility:public"],
        tags = [TEST_SRCS],
    )

    kwargs["srcs"] = [":" + srcs_name]

    if not (type == UNIT or type == INTEGRATION):
        fail("The 'type' attribute must be either UNIT or INTEGRATION")

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    kwargs["copts"] = local_includes + kwargs.get("copts", [])
    kwargs["linkstatic"] = kwargs.get("linkstatic", True)
    kwargs["name"] = name
    kwargs["tags"] = [TEST, type] + kwargs.get("tags", [])
    kwargs["target_compatible_with"] = kwargs.get("target_compatible_with", []) + _test_compatible_with()
    native.cc_test(**kwargs)
