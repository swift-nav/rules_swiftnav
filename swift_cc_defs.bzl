# Name for a unit test
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

def _common_c_opts(nocopts, pedantic = False):
    copts = [
        "-Wall",
        "-Werror",
        "-Wcast-align",
#        "-Wunused-but-set-parameter",
#        "-Wno-free-nonheap-object",
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
        #"-Wmissing-include-dirs",
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
    ]

    # filter nocopts from the list
    copts = [copt for copt in copts if copt not in nocopts]

    if pedantic:
        copts.append("-pedantic")

    return copts

def swift_cc_library(**kwargs):
    """Wraps cc_library to enforce standards for a production library.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = True)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_library(**kwargs)


def swift_cc_tool_library(**kwargs):
    """Wraps cc_library to enforce standards for a non-production library.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = False)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_library(**kwargs)


def swift_cc_binary(**kwargs):
    """Wraps cc_binary to enforce standards for a production binary.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = True)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_binary(**kwargs)


def swift_cc_tool(**kwargs):
    """Wraps cc_binary to enforce standards for a non-production binary.
    """
    nocopts = kwargs.pop("nocopts", [])

    copts = _common_c_opts(nocopts, pedantic = False)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_binary(**kwargs)


def swift_cc_test_library(**kwargs):
    """Wraps cc_library to enforce Swift test library conventions.
    """
    native.cc_library(**kwargs)


def swift_cc_test(name, type, **kwargs):
    """Wraps cc_test to enforce Swift testing conventions.

    Args:
        name: A unique name for this rule.
        type: Specifies whether the test is a unit or integration test.

            These are passed to cc_test as tags which enables running
            these test types seperately: `bazel test --test_tag_filters=unit //...`
    """

    if not (type == UNIT or type == INTEGRATION):
        fail("The 'type' attribute must be either UNIT or INTEGRATION")

    kwargs["name"] = name
    kwargs["tags"] = (kwargs["tags"] if "tags" in kwargs else []) + [type]
    native.cc_test(**kwargs)
