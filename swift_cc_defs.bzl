# Name for a unit test
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

def _common_c_opts(pedantic = False):
    copts = [
        "-Wall",
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

    if pedantic:
        copts.append("-pedantic")

    return copts


def _common_features(**kwargs):
    return [
        "treat_warnings_as_errors", # Not available until Bazel 6.0!
        "c99_standard",
        "cxx14_standard",
        "no_rtti",
        "no_exceptions",
    ]


def swift_cc_library(**kwargs):
    """Wraps cc_library to enforce standards for a production library.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features

    copts = _common_c_opts(pedantic = True)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_library(**kwargs)


def swift_cc_tool_library(**kwargs):
    """Wraps cc_library to enforce standards for a non-production library.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features

    copts = _common_c_opts(pedantic = False)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_library(**kwargs)


def swift_cc_binary(**kwargs):
    """Wraps cc_binary to enforce standards for a production binary.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features

    copts = _common_c_opts(pedantic = True)
    kwargs["copts"] = (kwargs["copts"] if "copts" in kwargs else []) + copts

    native.cc_binary(**kwargs)


def swift_cc_tool(**kwargs):
    """Wraps cc_binary to enforce standards for a non-production binary.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features

    copts = _common_c_opts(pedantic = False)
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
