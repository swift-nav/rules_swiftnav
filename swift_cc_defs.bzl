# Name for a unit test
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

def _common_features(**kwargs):
    return [
        "c99_standard",
        "cxx14_standard", 
        "no_rtti", 
        "no_exceptions",
        "warnings",
        "werror",
    ]

def swift_cc_library(**kwargs):
    """Wraps cc_library to enforce standards for a production library.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features
    native.cc_library(**kwargs)

def swift_cc_tool_library(**kwargs):
    """Wraps cc_library to enforce standards for a non-production library.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features
    native.cc_library(**kwargs)

def swift_cc_binary(**kwargs):
    """Wraps cc_binary to enforce standards for a production binary.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features
    native.cc_binary(**kwargs)

def swift_cc_tool(**kwargs):
    """Wraps cc_binary to enforce standards for a non-production binary.
    """
    features = _common_features()
    kwargs["features"] = (kwargs["features"] if "features" in kwargs else []) + features
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
