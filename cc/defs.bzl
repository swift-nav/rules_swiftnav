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

load(":utils.bzl", "construct_local_include")

# Name for a unit test
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

def _common_c_opts(nocopts, pedantic = False):
    # The following are set by default by Bazel:
    # -Wall, -Wunused-but-set-parameter, -Wno-free-heap-object
    copts = [
        "-Werror",
        "-Wcast-align",
        "-Wcast-qual",
        "-Wchar-subscripts",
        "-Wcomment",
        "-Wconversion",
        "-Wdisabled-optimization",
        "-Wextra",
        "-Wfloat-equal",
        "-Wformat",
        "-Wformat-security",
        "-Wformat-y2k",
        "-Wimplicit-fallthrough",
        "-Wimport",
        "-Winit-self",
        "-Winvalid-pch",
        "-Wmissing-braces",
        "-Wmissing-field-initializers",
        "-Wparentheses",
        "-Wpointer-arith",
        "-Wredundant-decls",
        "-Wreturn-type",
        "-Wsequence-point",
        "-Wshadow",
        "-Wsign-compare",
        "-Wstack-protector",
        "-Wswitch",
        "-Wswitch-default",
        "-Wswitch-enum",
        "-Wtrigraphs",
        "-Wuninitialized",
        "-Wunknown-pragmas",
        "-Wunreachable-code",
        "-Wunused",
        "-Wunused-function",
        "-Wunused-label",
        "-Wunused-parameter",
        "-Wunused-value",
        "-Wunused-variable",
        "-Wvolatile-register-var",
        "-Wwrite-strings",
        "-Wno-error=deprecated-declarations",
        #TODO: [BUILD-405] - Figure out why build breaks with this flag
        #"-Wmissing-include-dirs"
    ]

    # filter nocopts from the default list
    copts = [copt for copt in copts if copt not in nocopts]

    if pedantic:
        copts.append("-pedantic")

    return copts

def _construct_local_includes(local_includes):
    return [construct_local_include(path) for path in local_includes]

def swift_cc_library(**kwargs):
    """Wraps cc_library to enforce standards for a production library.

    Primarily this consists of a default set of compiler options and
    language standards.

    Production targets (swift_cc*), are compiled with the -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_library

            The following additional attributes are supported:

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])  # pop because nocopts is a deprecated cc* attr.

    copts = _common_c_opts(nocopts, pedantic = True)
    copts = local_includes + copts
    kwargs["copts"] = copts + (kwargs["copts"] if "copts" in kwargs else [])

    native.cc_library(**kwargs)

def swift_cc_tool_library(**kwargs):
    """Wraps cc_library to enforce standards for a non-production library.

    Primarily this consists of a default set of compiler options and
    language standards.

    Non-production targets (swift_cc_tool*), are compiled without the
    -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_library

            The following additional attributes are supported:

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = False)
    copts = local_includes + copts
    kwargs["copts"] = copts + (kwargs["copts"] if "copts" in kwargs else [])

    native.cc_library(**kwargs)

def swift_cc_binary(**kwargs):
    """Wraps cc_binary to enforce standards for a production binary.

    Primarily this consists of a default set of compiler options and
    language standards.

    Production targets (swift_cc*), are compiled with the -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_binary

            The following additional attributes are supported:

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = True)
    copts = local_includes + copts
    kwargs["copts"] = copts + (kwargs["copts"] if "copts" in kwargs else [])

    native.cc_binary(**kwargs)

def swift_cc_tool(**kwargs):
    """Wraps cc_binary to enforce standards for a non-production binary.

    Primarily this consists of a default set of compiler options and
    language standards.

    Non-production targets (swift_cc_tool*), are compiled without the
    -pedantic flag.

    Args:
        **kwargs: See https://bazel.build/reference/be/c-cpp#cc_binary

            The following additional attributes are supported:

            local_includes: List of local (non-public) include paths. Prefer
            this to passing local includes using copts. Paths are expected to
            be relative to the package this macro is called from.

            nocopts: List of flags to remove from the default compile
            options. Use judiciously.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = False)
    kwargs["copts"] = copts + (kwargs["copts"] if "copts" in kwargs else [])

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

    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + local_includes
    native.cc_library(**kwargs)

def swift_cc_test(name, type, **kwargs):
    """Wraps cc_test to enforce Swift testing conventions.

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

    if not (type == UNIT or type == INTEGRATION):
        fail("The 'type' attribute must be either UNIT or INTEGRATION")

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + local_includes
    kwargs["name"] = name
    kwargs["tags"] = (kwargs["tags"] if "tags" in kwargs else []) + [type]
    native.cc_test(**kwargs)
