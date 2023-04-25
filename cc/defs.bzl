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
load(":copts.bzl", "DEFAULT_COPTS", "GCC5_COPTS", "GCC6_COPTS")
load(":cc_static_library.bzl", _cc_static_library = "cc_static_library")

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

STAMPED_LIB_SUFFIX = ".stamped"

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
        Label("//cc/constraints:gcc-5"): [copt for copt in GCC5_COPTS if copt not in nocopts],
        "//conditions:default": [copt for copt in DEFAULT_COPTS if copt not in nocopts],
    }) + select({
        Label("//cc:_disable_warnings_as_errors"): [],
        "//conditions:default": ["-Werror"],
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

# Disable building when --//:disable_tests=true or when building on windows
def _test_compatible_with():
    return select({
        Label("//cc:_disable_tests"): ["@platforms//:incompatible"],
        "@platforms//os:windows": ["@platforms//:incompatible"],
        "//conditions:default": [],
    })

def _create_srcs(**kwargs):
    native.filegroup(
        name = kwargs.get("name") + ".srcs",
        srcs = kwargs.get("srcs", []),
        visibility = kwargs.get("visibility", ["//visibility:private"]),
    )

def _create_hdrs(**kwargs):
    native.filegroup(
        name = kwargs.get("name") + ".hdrs",
        srcs = kwargs.get("hdrs", []),
        visibility = kwargs.get("visibility", ["//visibility:private"]),
    )

def cc_stamped_library(name, out, template, hdrs, includes, defaults, visibility = None):
    """Creates a cc_library stamped with non-hermetic build metadata.

    Creates a cc_library from the input template with values of the form @VAL@
    substituted with values from the workspace status program. This typically
    includes version control information, timestamps, and other similiar
    data. The output file is only compiled into the final resulting binary.

    Also creates an additional library target appended with ".stamped". This
    variant has the stamped symbols included directly into the resulting
    artifact. Its only intended to be used when creating a static archive
    bundle with cc_static_archive.

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

    # This variant has the stamped symbols in the archive
    swift_cc_library(
        name = name + STAMPED_LIB_SUFFIX,
        srcs = [source_name],
        visibility = visibility,
    )

    # This variant forwards the stamped symbols to the final link
    swift_cc_library(
        name = name,
        hdrs = hdrs,
        includes = includes,
        linkstamp = source_name,
        visibility = visibility,
    )

def cc_static_library(name, deps, visibility = ["//visibility:private"]):
    _cc_static_library(
        name = name,
        deps = deps,
        target_compatible_with = select({
            # Creating static libraries is not supported by macos yet.
            "@platforms//os:macos": ["@platforms//:incompatible"],
            "//conditions:default": [],
        }),
        visibility = visibility,
    )

def swift_c_library(**kwargs):
    """Wraps cc_library to enforce standards for a production c library.

    Primarily this consists of a default set of compiler options and
    language standards. This rule also creates 'target_name.srcs' and
    'target_name.hdrs' targets that contain sources and headers,
    respectively.

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
    _create_srcs(**kwargs)
    _create_hdrs(**kwargs)

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])  # pop because nocopts is a deprecated cc* attr.

    copts = _common_cc_opts(nocopts, pedantic = True)
    copts = local_includes + copts

    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", 99)

    c_standard = _c_standard(extensions, standard)

    kwargs["copts"] = copts + c_standard + kwargs.get("copts", [])

    kwargs["tags"] = [LIBRARY] + kwargs.get("tags", [])

    native.cc_library(**kwargs)

def swift_cc_library(**kwargs):
    """Wraps cc_library to enforce standards for a production c++ library.

    Primarily this consists of a default set of compiler options and
    language standards. This rule also creates 'target_name.srcs' and
    'target_name.hdrs' targets that contain sources and headers,
    respectively.

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
    _create_srcs(**kwargs)
    _create_hdrs(**kwargs)

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])  # pop because nocopts is a deprecated cc* attr.

    copts = _common_cc_opts(nocopts, pedantic = True)
    copts = local_includes + copts

    exceptions = kwargs.pop("exceptions", False)
    rtti = kwargs.pop("rtti", False)
    standard = kwargs.pop("standard", None)

    cxxopts = _common_cxx_opts(exceptions, rtti, standard)

    kwargs["copts"] = copts + cxxopts + kwargs.get("copts", [])

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
    of the test. The name of the sources is created with the '.srcs' suffix.

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

    srcs_name = name + ".srcs"
    srcs = kwargs.get("srcs", [])

    native.filegroup(
        name = srcs_name,
        srcs = srcs,
        visibility = ["//visibility:public"],
        tags = [TEST_SRCS],
        target_compatible_with = kwargs.get("target_compatible_with", []),
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
