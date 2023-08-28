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

load("//stamp:stamp_file.bzl", "stamp_file")
load(":utils.bzl", "construct_local_include")
load(":new_copts.bzl", "get_common_cc_opts")
load(":cc_static_library.bzl", _cc_static_library = "cc_static_library")

TEST = "test"

TEST_SRCS = "test_srcs"

LIBRARY = "library"

# Name for a unit test
UNIT = "unit"

# Name for a integration test
INTEGRATION = "integration"

INTERNAL = "internal"

PROD = "prod"

PORTABLE = "portable"

SAFE = "safe"

STAMPED_LIB_SUFFIX = ".stamped"

def _validate_kwargs(level, forbidden, kwargs):
  """Doc
    print("tidy")
    print(target)
  """

  for f in forbidden:
    if f in kwargs:
      fail("'" + f + "' not permitted in " + level + " targets")


def new_cc_stamped_library(name, out, template, hdrs, includes, defaults, level, visibility = None):
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
        level: Coding standard level
        visibility: See https://bazel.build/reference/be/common-definitions#common.visibility
    """

    source_name = name + "_"

    stamp_file(name = source_name, out = out, defaults = defaults, template = template)

    # This variant has the stamped symbols in the archive
    swift_new_cc_library(
        name = name + STAMPED_LIB_SUFFIX,
        srcs = [source_name],
        visibility = visibility,
        level = level,
    )

    # This variant forwards the stamped symbols to the final link
    swift_new_cc_library(
        name = name,
        hdrs = hdrs,
        includes = includes,
        linkstamp = source_name,
        visibility = visibility,
        level = level,
    )

def swift_new_internal_cc_library(**kwargs):
    kwargs["level"] = INTERNAL

    swift_new_cc_library(**kwargs)

def swift_new_internal_c_library(**kwargs):
  kwargs["level"] = INTERNAL

  swift_new_c_library(**kwargs)

def swift_new_prod_cc_library(**kwargs):
    _validate_kwargs(PROD, ["nocopts"], kwargs)

    kwargs["level"] = PROD

    swift_new_cc_library(**kwargs)

def swift_new_prod_c_library(**kwargs):
  _validate_kwargs(PROD, ["nocopts"], kwargs)

  kwargs["level"] = PROD

  swift_new_c_library(**kwargs)

def swift_new_portable_cc_library(**kwargs):
    _validate_kwargs(PORTABLE, ["standard", "extensions", "nocopts"], kwargs)

    kwargs["level"] = PORTABLE

    swift_new_cc_library(**kwargs)

def swift_new_portable_c_library(**kwargs):
  _validate_kwargs(PORTABLE, ["standard", "extensions", "nocopts"], kwargs)

  kwargs["level"] = PORTABLE

  swift_new_c_library(**kwargs)

def swift_new_safe_cc_library(**kwargs):
    _validate_kwargs(SAFE, ["standard", "extensions", "nocopts"], kwargs)

    kwargs["level"] = SAFE

    swift_new_cc_library(**kwargs)

def swift_new_safe_c_library(**kwargs):
  _validate_kwargs(SAFE, ["standard", "extensions", "nocopts"], kwargs)

  kwargs["level"] = SAFE

  swift_new_c_library(**kwargs)

def _construct_local_includes(local_includes):
    return [construct_local_include(path) for path in local_includes]

# Form the c standard string
def _c_standard(extensions = False, standard = 99):
    extensions = "gnu" if extensions else "c"
    return ["-std={}{}".format(extensions, standard)]

# Form the c++ standard string.
def _cxx_standard(default, override):
    return default if not override else "-std=c++{}".format(override)

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

# Disable building when --//:disable_tests=true or when building on windows
def _test_compatible_with():
    return select({
        Label("//cc:_disable_tests"): ["@platforms//:incompatible"],
        "@platforms//os:windows": ["@platforms//:incompatible"],
        "//conditions:default": [],
    })

def _symbolizer_env(val):
    return select({
        # The + operator is not supported on dict and select types so we need to be
        # clever here.
        Label("//cc:enable_symbolizer_x86_64_linux"): dict(val, **{"ASAN_SYMBOLIZER_PATH": "$(location @x86_64-linux-llvm//:symbolizer)"}),
        Label("//cc:enable_symbolizer_x86_64_darwin"): dict(val, **{"ASAN_SYMBOLIZER_PATH": "$(location @x86_64-darwin-llvm//:symbolizer)"}),
        "//conditions:default": {},
    })

def _symbolizer_data():
    return select({
        Label("//cc:enable_symbolizer_x86_64_linux"): ["@x86_64-linux-llvm//:symbolizer"],
        Label("//cc:enable_symbolizer_x86_64_darwin"): ["@x86_64-darwin-llvm//:symbolizer"],
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

def swift_new_cc_library(**kwargs):
  print(kwargs)
  print(kwargs["level"])
  local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

  _create_srcs(**kwargs)
  _create_hdrs(**kwargs)

  level = kwargs.pop("level")
  if level not in [INTERNAL, PROD, PORTABLE, SAFE]:
    fail("Invalid level")

  provided_copts = kwargs.pop("copts", [])
  provided_nocopts = kwargs.pop("nocopts", [])
  print('here')
  print(provided_nocopts)
  if "-fexceptions" in provided_copts or "-fno-exceptions" in provided_copts:
    fail("Do not try to control exceptions by passing copts, use the exceptions field instead")
  if "-frtti" in provided_copts or "-fno-rtti" in provided_copts:
    fail("Do not try to control RTTI by passing copts, use the rtti field instead")

  copts = get_common_cc_opts(level, provided_copts, provided_nocopts) + local_includes

  exceptions = kwargs.pop("exceptions", False)
  rtti = kwargs.pop("rtti", False)
  standard = kwargs.pop("standard", None)

  cxxopts = _common_cxx_opts(exceptions, rtti, standard)

  kwargs["copts"] = copts + cxxopts
  kwargs["data"] = kwargs.get("data", []) + _symbolizer_data()
  #kwargs["env"] = _symbolizer_env(kwargs.get("env", {}))
  kwargs["tags"] = [level, LIBRARY] + kwargs.get("tags", [])

  native.cc_library(**kwargs)

def swift_new_c_library(**kwargs):
  level = kwargs.pop("level")
  if level not in [INTERNAL, PROD, PORTABLE, SAFE]:
    fail("Invalid level")

  local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

  nocopts = kwargs.pop("nocopts", [])

  copts = get_common_cc_opts(level, kwargs.get("copts", []), nocopts)
  copts = local_includes + copts

  extensions = kwargs.pop("extensions", False)
  standard = kwargs.pop("standard", 99)

  c_standard = _c_standard(extensions, standard)

  kwargs["copts"] = copts + c_standard
  kwargs["tags"] = [level, LIBRARY] + kwargs.get("tags", [])

  native.cc_library(**kwargs)

def swift_new_cc_test(name, type, **kwargs):

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
    kwargs["data"] = kwargs.get("data", []) + _symbolizer_data()
    kwargs["env"] = _symbolizer_env(kwargs.get("env", {}))
    kwargs["linkstatic"] = kwargs.get("linkstatic", True)
    kwargs["name"] = name
    kwargs["tags"] = [TEST, type, INTERNAL] + kwargs.get("tags", [])
    kwargs["target_compatible_with"] = kwargs.get("target_compatible_with", []) + _test_compatible_with()

    native.cc_test(**kwargs)
