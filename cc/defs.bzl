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

def _common_c_opts(nocopts, pedantic = False):
    return select({
        Label("//cc/constraints:gcc-6"): [copt for copt in GCC6_COPTS if copt not in nocopts],
        "//conditions:default": [copt for copt in DEFAULT_COPTS if copt not in nocopts],
    }) + ["-pedantic"] if pedantic else []

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
    kwargs["tags"] = (kwargs["tags"] if "tags" in kwargs else []) + [LIBRARY]

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
    kwargs["tags"] = (kwargs["tags"] if "tags" in kwargs else []) + [BINARY]

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
    kwargs["tags"] = (kwargs["tags"] if "tags" in kwargs else []) + [TEST_LIBRARY]
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
    kwargs["tags"] = (kwargs["tags"] if "tags" in kwargs else []) + [type] + [TEST]
    native.cc_test(**kwargs)
