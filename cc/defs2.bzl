"""Swift wrappers for native cc rules."""

load("//stamp:stamp_file.bzl", "stamp_file")
load(":cc_static_library.bzl", _cc_static_library = "cc_static_library")
load(":utils.bzl", "construct_local_include")

# Broad target catagories

# A unit/integration tests. Executable during `bazel test` invocations
TEST = "test"

# A compiled library
LIBRARY = "library"

# An executable
BINARY = "binary"

# Unit test, probably using a unit testing framework such as
# gtest or check. Tests a small software component, typically
# short lived. Not long running, not end-to-end tests
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

TEST_SRCS = "test_srcs"

# Coding Standard levels
#
# Throughout this file and others there are references to coding
# standard levels. In Swift code there are 3 levels, 2 of which
# each have a sub variant.
#
# The levels are:
# - Safe: Code to be used in safety of life situations
# - Production: Code used in production environments but which does not require ISO26262 assessment
# - Internal: All other code, including test suites, internal utilities. Code which doesn't see production use
#
# The Safe and Production levels each have a variant:
# - Portable: Code which is expected to run on a wide variant of software/hardware targets and must be extremely portable
#
# These combine to make 5 different kinds of targets:
#
# safe:
#   Safety of life code which must be highly portable.
#   Strictest set of compiler warnings
#   Highest level of static analysis
#   Uses full Autosar coding standards
#   C++14, C99 only
#   Compiler extensions disabled but may be explicitly requested
#   Not allowed to remove compiler warnings but may add them
#   Permitted to link against "safe" and "safe-portable" targets only
#
# safe-portable:
#   The same as "safe" plus:
#   No compiler extensions
#   Requires strict compliance with language spec (-pedantic used with GCC/Clang)
#   Permitted to link against "safe-portable" targets only
#
# prod:
#   Enables most compiler warnings and static analysis checks
#   except any which pose a drag on developer workflow and do
#   not have a noticeable effect on code quality
#   Language standards may be chosen but default to C++14, C99
#   Compiler extensions disabled but may be explicitly requested
#   Not allowed to remove compiler warnings but may add them
#   Permitted to link against all target types except "internal"
#
# prod-portable:
#   Same as "prod" plus:
#   No compiler extensions
#   Requires strict compliance with language spec (-pedantic used with GCC/Clang)
#   Permitted to link against "prod-portable" and "safe-portable" targets only
#
# internal:
#   Basic sanity compiler warnings
#   Basic static analysis checks
#   Fairly permissive with only major errors checked by default
#   C++14, C99 default
#   Compiler extensions disabled but may be explicitly requested
#   Allowed to add or remove compiler flags
#   Permitted to link against any other target type
#
#
# Tests are created through a separate macro but they all take the
# "internal" level. A notable difference for test suites is that they
# have exceptions and RTTI enabled by default (all other levels both
# features are disabled by default)

# Internal coding standard level
INTERNAL = "internal"

# Production coding standard level
PROD = "prod"

# Safe coding standard level
SAFE = "safe"

def _create_srcs(**kwargs):
    native.filegroup(
        name = kwargs.get("name") + ".srcs",
        srcs = kwargs.get("srcs", []),
        visibility = kwargs.get("visibility", ["//visibility:public"]),
    )

def _create_hdrs(**kwargs):
    native.filegroup(
        name = kwargs.get("name") + ".hdrs",
        srcs = kwargs.get("hdrs", []),
        visibility = kwargs.get("visibility", ["//visibility:public"]),
    )

def _any_of_in(keys, features):
    for k in keys:
        if k in features:
            return True
    return False

def _check_features_misuse(features):
    if "gnu_extensions" in features:
        fail("Do not enable gnu_extensions features manually, pass extensions=True instead")
    if _any_of_in(["c89", "c90", "c99", "c11", "c17", "c++98", "c++11", "c++14", "c++17", "c++20", "c++23"], features):
        fail("Do not set language standards manually, pass standard=n instead")
    if _any_of_in(["prod_coding_standard", "internal_coding_standard", "safe_coding_standard", "portable_coding_standard"], features):
        fail("Do not try to control coding standard manually, use the correct macro to create a target")

def _get_lang_features(lang, extensions, standard, portable):
    """
    Get toolchain features which need to be enable for given language standard and extensions
    gnu_extensions may not be the best choice of names here
    """

    lang_standard_feature = ""
    lang_extensions_feature = []
    if lang == "c":
        if standard == None:
            standard = 99
        if standard not in [89, 90, 99, 11, 17]:
            fail("Invalid C standard")
        lang_standard_feature = ["c" + str(standard)]
    elif standard != None:
        if standard not in [98, 11, 14, 17, 20]:
            fail("Invalid CXX standard")
        lang_standard_feature = ["c++" + str(standard)]
    else:
        lang_standard_feature = select({
            Label("@rules_swiftnav//cc:cxx17"): ["c++17"],
            Label("@rules_swiftnav//cc:cxx20"): ["c++20"],
            Label("@rules_swiftnav//cc:cxx23"): ["c++23"],
            "//conditions:default": ["c++14"],
        })

    if extensions and portable:
        fail("Compiler extensions may not be enabled on portable targets")

    if extensions:
        lang_extensions_feature.append("gnu_extensions")

    if portable:
        lang_extensions_feature.append("portable_coding_standard")

    return (lang_standard_feature, lang_extensions_feature)

def _get_exceptions_rtti_features(lang, exceptions, rtti):
    if lang == "c":
        if rtti:
            fail("Enabling RTTI is meaningless with C targets")
        if exceptions:
            fail("Enabling exceptions is meaningless with C targets")
        return []

    return select({
        Label("@rules_swiftnav//cc:_enable_exceptions"): ["exceptions_feature"],
        "//conditions:default": ["noexceptions_feature" if not exceptions else "exceptions_feature"],
    }) + select({
        Label("@rules_swiftnav//cc:_enable_rtti"): ["rtti_feature"],
        "//conditions:default": ["nortti_feature" if not rtti else "rtti_feature"],
    })

def _get_warnings_features(level):
    return [level + "_coding_standard"]

def _check_copts_misuse(copt_flag, key, copts, nocopts):
    """
    Check for misuse of copts and nocopts options to target macros

    Certain features such as exceptions or RTTI as controlled through
    options to the target macros. Many developers will try to pass
    compiler flags directly through copts or nocopts, this helper
    function will catch this and fail the build
    """
    if copt_flag in copts or copt_flag in nocopts:
        fail("Do not try to pass {} in copts or nocopts, use the {} key instead".format(copt_flag, key))

def _validate_copts_nocopts(level, portable, copts, nocopts):
    _check_copts_misuse("-frtti", "rtti", copts, nocopts)
    _check_copts_misuse("-fno-rtti", "rtti", copts, nocopts)
    _check_copts_misuse("-fexceptions", "exceptions", copts, nocopts)
    _check_copts_misuse("-fno-exceptions", "exceptions", copts, nocopts)
    _check_copts_misuse("-pedantic", "language standard compliance", copts, nocopts)

    if level in [PROD, SAFE]:
        if len(nocopts) > 0:
            fail("Passing nocopts to production or safe targets is not allowed. Only adding flags via copts is permitted")

    for f in copts:
      if f.startswith("-W") or f.startswith("-Wno'"):
        if portable:
          fail("Don't use non-portable compile flags with portable targets (eg, -W or -Wno-")
    for f in nocopts:
      if f.startswith("-W") or f.startswith("-Wno'"):
        if portable:
          fail("Don't use non-portable compile flags with portable targets (eg, -W or -Wno-")


def _build_copts(copts, nocopts):
    return [f for f in copts if f not in nocopts]

# Handle various nuances of local include paths
def _construct_local_includes(local_includes):
    ret = []
    for path in local_includes:
        ret += construct_local_include(path)
    return ret

# Disable building when --//:disable_tests=true or when building on windows
def _test_compatible_with():
    return select({
        Label("@rules_swiftnav//cc:_disable_tests"): ["@platforms//:incompatible"],
        "@platforms//os:windows": ["@platforms//:incompatible"],
        "//conditions:default": [],
    })

def _add_library(**kwargs):
    """
    Add a library target. Generic function to be called from a wrapper macro
    which properly sets the coding standard level
    """

    features = kwargs.pop("features", [])

    _check_features_misuse(features)

    level = kwargs.pop("level")
    portable = kwargs.pop("portable", False)
    lang = kwargs.pop("lang")
    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", None)

    (lang_standard_feature, lang_extensions_feature) = _get_lang_features(lang, extensions, standard, portable)

    exceptions_rtti_features = _get_exceptions_rtti_features(lang, kwargs.pop("exceptions", None), kwargs.pop("rtti", None))

    warnings_features = _get_warnings_features(level)

    copts = kwargs.pop("copts", [])
    nocopts = kwargs.pop("nocopts", [])

    _validate_copts_nocopts(level, portable, copts, nocopts)

    copts = _build_copts(copts, nocopts)

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))
    for i in local_includes:
        copts.append(i)

    kwargs["copts"] = copts
    kwargs["features"] = warnings_features + lang_standard_feature + lang_extensions_feature + exceptions_rtti_features + select({
        Label("//cc:_disable_warnings_as_errors"): [],
        "//conditions:default": ["treat_warnings_as_errors"],
    }) + features

    kwargs["tags"] = [LIBRARY, level] + (["portable"] if portable else []) + kwargs.get("tags", [])
    kwargs["target_compatible_with"] = kwargs.get("target_compatible_with", [])

    if "test_library" in kwargs["tags"]:
      kwargs["tags"].append("test_srcs")

    _create_srcs(**kwargs)
    _create_hdrs(**kwargs)

    native.cc_library(**kwargs)

def _add_binary(**kwargs):
    """
    Add an executable target. Generic function to be called from a wrapper macro
    which properly sets the coding standard level
    """

    features = kwargs.pop("features", [])

    _check_features_misuse(features)

    level = kwargs.pop("level")
    portable = kwargs.pop("portable", False)
    lang = kwargs.pop("lang")
    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", None)

    (lang_standard_feature, lang_extensions_feature) = _get_lang_features(lang, extensions, standard, portable)

    exceptions_rtti_features = _get_exceptions_rtti_features(lang, kwargs.pop("exceptions", None), kwargs.pop("rtti", None))

    warnings_features = _get_warnings_features(level)

    copts = kwargs.pop("copts", [])
    nocopts = kwargs.pop("nocopts", [])

    _validate_copts_nocopts(level, portable, copts, nocopts)

    copts = _build_copts(copts, nocopts)

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))
    for i in local_includes:
        copts.append(i)

    kwargs["copts"] = copts
    kwargs["features"] = warnings_features + lang_standard_feature + lang_extensions_feature + exceptions_rtti_features + select({
        Label("//cc:_disable_warnings_as_errors"): [],
        "//conditions:default": ["treat_warnings_as_errors"],
    }) + features

    kwargs["tags"] = [BINARY, level] + (["portable"] if portable else []) + kwargs.get("tags", [])
    kwargs["target_compatible_with"] = kwargs.get("target_compatible_with", [])

    _create_srcs(**kwargs)
    _create_hdrs(**kwargs)

    native.cc_binary(**kwargs)

def _add_test(**kwargs):
    """
    Add a library target. Generic function to be called from a wrapper macro
    which properly sets the coding standard level
    """

    features = kwargs.pop("features", [])

    _check_features_misuse(features)

    level = INTERNAL
    portable = kwargs.pop("portable", False)
    lang = kwargs.pop("lang")
    extensions = kwargs.pop("extensions", False)
    standard = kwargs.pop("standard", None)

    (lang_standard_feature, lang_extensions_feature) = _get_lang_features(lang, extensions, standard, portable)

    exceptions_rtti_features = _get_exceptions_rtti_features(lang, kwargs.pop("exceptions", True), kwargs.pop("rtti", True))

    warnings_features = _get_warnings_features(level)

    copts = kwargs.pop("copts", [])
    nocopts = kwargs.pop("nocopts", [])

    _validate_copts_nocopts(level, portable, copts, nocopts)

    copts = _build_copts(copts, nocopts)

    local_includes = _construct_local_includes(kwargs.pop("local_includes", []))
    for i in local_includes:
        copts.append(i)

    kwargs["copts"] = copts
    kwargs["features"] = warnings_features + lang_standard_feature + lang_extensions_feature + exceptions_rtti_features + select({
        Label("//cc:_disable_warnings_as_errors"): [],
        "//conditions:default": ["treat_warnings_as_errors"],
    }) + ["disable_warnings_for_test_targets"] + features

    if "type" not in kwargs:
        fail("Type must be given for tests, either UNIT or INTEGRATION")

    type = kwargs.pop("type")
    if not (type == UNIT or type == INTEGRATION):
        fail("The 'type' attribute must be either UNIT or INTEGRATION")

    kwargs["tags"] = [BINARY, TEST, level, type] + kwargs.get("tags", [])

    kwargs["target_compatible_with"] = kwargs.get("target_compatible_with", []) + _test_compatible_with()

    _create_srcs(**kwargs)
    _create_hdrs(**kwargs)

    native.cc_test(**kwargs)

def _assert_no_reserved_keys(**kwargs):
    if "lang" in kwargs:
        fail("Do not try to specify language manually")
    if "level" in kwargs:
        fail("Do not try to specify coding standard manually")

def swift_internal_c_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "c", level = INTERNAL, **kwargs)

def swift_prod_c_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "c", level = PROD, **kwargs)

def swift_prod_portable_c_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "c", level = PROD, portable = True, **kwargs)

def swift_safe_c_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "c", level = SAFE, **kwargs)

def swift_safe_portable_c_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "c", level = SAFE, portable = True, **kwargs)

def swift_internal_c_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "c", level = INTERNAL, **kwargs)

def swift_prod_c_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "c", level = PROD, **kwargs)

def swift_prod_portable_c_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "c", level = PROD, portable = True, **kwargs)

def swift_safe_c_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "c", level = SAFE, **kwargs)

def swift_safe_portable_c_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "c", level = SAFE, portable = True, **kwargs)

def swift_new_c_test(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_test(lang = "c", rtti = False, exceptions = False, **kwargs)

def swift_internal_cc_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "cc", level = INTERNAL, **kwargs)

def swift_prod_cc_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "cc", level = PROD, **kwargs)

def swift_prod_portable_cc_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "cc", level = PROD, portable = True, **kwargs)

def swift_safe_cc_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "cc", level = SAFE, **kwargs)

def swift_safe_portable_cc_binary(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_binary(lang = "cc", level = SAFE, portable = True, **kwargs)

def swift_internal_cc_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "cc", level = INTERNAL, **kwargs)

def swift_prod_cc_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "cc", level = PROD, **kwargs)

def swift_prod_portable_cc_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "cc", level = PROD, portable = True, **kwargs)

def swift_safe_cc_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "cc", level = SAFE, **kwargs)

def swift_safe_portable_cc_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)
    _add_library(lang = "cc", level = SAFE, portable = True, **kwargs)

def swift_cc_test_library(**kwargs):
    _assert_no_reserved_keys(**kwargs)

    if "rtti" not in kwargs:
        kwargs["rtti"] = True
    if "exceptions" not in kwargs:
        kwargs["exceptions"] = True

    if "tags" not in kwargs:
      kwargs["tags"] = []
    kwargs["tags"].append("test_library")

    kwargs["target_compatible_with"] = _test_compatible_with()

    _add_library(lang = "cc", level = INTERNAL, portable = False, **kwargs)

def swift_new_cc_test(**kwargs):
    _assert_no_reserved_keys(**kwargs)

    # level doesn't need to be specified for tests, it's always INTERNAL
    _add_test(lang = "cc", **kwargs)

STAMPED_LIB_SUFFIX = ".stamped"

def new_cc_stamped_library(name, out, template, hdrs, includes, defaults, visibility = None):
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
    swift_safe_portable_cc_library(
        name = name + STAMPED_LIB_SUFFIX,
        srcs = [source_name],
        visibility = visibility,
    )

    # This variant forwards the stamped symbols to the final link
    swift_safe_portable_cc_library(
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

