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
load("@rules_swiftnav//cc:utils.bzl", "construct_local_include")
load("@rules_swiftnav//cc:cc_static_library.bzl", _cc_static_library = "cc_static_library")

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

# Production (non-portable) coding standard level
PROD = "prod"

# Production portable coding standard level
PROD_PORTABLE = "prod-portable"

# Safe (non-portable) coding standard level
SAFE = "safe"

# Safe portable coding standard level
SAFE_PORTABLE = "safe-portable"

# Compiler flags which are known to be incompatible with GCC6
GCC6_INCOMPATIBLE_FLAGS = [
  "-Wimplicit-fallthrough",
]

# Compiler flags which are known to be incompatible with GCC5
GCC5_INCOMPATIBLE_FLAGS = [
  "-Wimplicit-fallthrough",
]

def _get_lang_flag(lang, extensions, standard):
  """
  Get an appropriate compiler switch to set:
  - The source language
  - The version of the language standard
  - Whether compiler extensions are enabled or not
  """
  extensions = "gnu" if extensions else "c"
  if lang == "c":
    return ["-std={}{}".format(extensions, 99 if standard == None else standard)]

  return select({
    Label("//cc:cxx17"): ["-std={}++{}".format(extensions, 17 if standard == None else standard)],
    Label("//cc:cxx20"): ["-std={}++{}".format(extensions, 20 if standard == None else standard)],
    Label("//cc:cxx23"): ["-std={}++{}".format(extensions, 23 if standard == None else standard)],
    "//conditions:default": ["-std={}++{}".format(extensions, 14 if standard == None else standard)],
  })

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

def _get_default_flags(lang, level):
  """
  Get a default set of compiler flags for a language and 
  coding standard level
  """
  base_flags = [
    # stupid clang
    "-Wno-format-security",
    "-Wno-integer-overflow",
  ]

  # Flags which relate to portable targets
  portable_flags = {
    "common": [
      "-pedantic",
      "-pedantic-errors",
      "-fstrict-aliasing",
      "-Wstrict-aliasing",
      "-Wcast-align",
      "-Wmain",
    ],
    "c": [
    ],
    "cc": [
    ]
  }

  # Flags to be applied to the internal level and upwards
  internal_flags = {
    "common": [
      "-Waddress",
      # "-Warray-bounds=1", # Disabled until clang is unfucked
      # "-Wbool-compare", # Disabled until clang is unfucked
      "-Wbool-operation",
      "-Wcast-function-type",
      "-Wchar-subscripts",
      # "-Wclobbered", # Disabled until clang is unfucked
      "-Wdangling-else",
      "-Wfloat-equal",
      "-Wignored-qualifiers",
      "-Winit-self",
      "-Winvalid-pch",
      "-Wlogical-not-parentheses",
      # "-Wmaybe-uninitialized", # Disabled until clang is unfucked
      # "-Wmemset-elt-size", # Disabled until clang is unfucked
      "-Wmemset-transposed-args",
      "-Wmisleading-indentation",
      # "-Wmismatched-dealloc", # Disabled until clang is unfucked
      # "-Wmissing-attributes", # Disabled until clang is unfucked
      "-Wmissing-field-initializers",
      # "-Wmultistatement-macros", # Disabled until clang is unfucked
      "-Wparentheses",
      # "-Wrestrict", # Disabled until clang is unfucked
      "-Wsequence-point",
      "-Wshift-negative-value",
      "-Wsizeof-array-div",
      "-Wsizeof-pointer-div",
      "-Wsizeof-pointer-memaccess",
      "-Wstring-compare",
      "-Wtautological-compare",
      "-Wtrigraphs",
      "-Wtype-limits",
      "-Wuninitialized",
      "-Wunknown-pragmas",
      "-Wwrite-strings",
    ],
    "c": [
      "-Warray-parameter=2",
      "-Wbad-function-cast",
      "-Wduplicate-decl-specifier",
      "-Wmissing-parameter-type",
      "-Wold-style-declaration",
    ],
    "cc": [
      # "-Wcatch-value", # Disabled until clang is unfucked
      "-Wdeprecated-copy",
      "-Wmismatched-new-delete",
    ]
  }

  # Flags to be applied to the prod level and upwards on top of the internal flags
  prod_flags = {
    "common": [
      "-Wall",
      "-Wextra",

      "-Wcast-qual",
      "-Wcomment",
      "-Wconversion",
      "-Wdisabled-optimization",
      "-Wempty-body",
      "-Wenum-compare",
      "-Wenum-conversion",
      #"-Wenum-int-mismatch",
      "-Wfloat-conversion",
      "-Wformat",
      "-Wformat-extra-args",
      "-Wformat-overflow",
      "-Wformat-security",
      "-Wformat-truncation",
      "-Wformat-y2k",
      "-Wimplicit-fallthrough=3",
      "-Wimport",
      "-Wint-in-bool-context",
      "-Wmissing-braces",
      "-Wnarrowing",
      "-Wno-error=deprecated-declarations",
      "-Wnonnull",
      "-Wnonnull-compare",
      "-Wopenmp-simd",
      "-Wredundant-decls",
      "-Wreturn-type",
      "-Wshadow",
      "-Wsign-compare",
      "-Wsign-conversion",
      "-Wstack-protector",
      "-Wstrict-aliasing",
      "-Wstrict-overflow=1",
      "-Wswitch",
      "-Wswitch-default",
      "-Wswitch-enum",
      "-Wunreachable-code",
      "-Wunused-but-set-parameter",
      "-Wunused-but-set-variable",
      "-Wunused-const-variable",
      "-Wunused-function",
      "-Wunused-label",
      "-Wunused-local-typedefs",
      "-Wunused-macros",
      "-Wunused-parameter",
      "-Wunused-result",
      "-Wunused-value",
      "-Wunused-variable",
      "-Wvla-parameter",
      "-Wvolatile-register-var",
      "-Wzero-length-bounds",
    ],
    "c": [
      "-Wimplicit",
      "-Wimplicit-function-declaration",
      "-Wimplicit-int",
      "-Woverride-init",
      "-Wpointer-sign",
    ],
    "cc": [
      "-Wc++11-compat",
      "-Wc++14-compat",
      "-Wc++17-compat",
      "-Wc++20-compat",
      "-Wpessimizing-move",
      "-Wrange-loop-construct",
      "-Wredundant-move",
      "-Wreorder",
      "-Wself-move",
    ]
  }

  # Flags to be applied to the safe level on top of the prod flags
  safe_flags = {
    "common": [
      "-Wpointer-arith",
    ],
    "c": [
    ],
    "cc": [
    ]
  }

  cflags = base_flags

  cflags += internal_flags['common']
  cflags += internal_flags[lang]

  if level == PROD or level == PROD_PORTABLE:
    cflags += prod_flags['common']
    cflags += prod_flags[lang]

  if level == SAFE or level == SAFE_PORTABLE:
    cflags += safe_flags['common']
    cflags += safe_flags[lang]

  if level == PROD_PORTABLE or level == SAFE_PORTABLE:
    cflags += portable_flags['common']
    cflags += portable_flags[lang]

  return cflags

def _construct_cflags(lang, level, rtti, exceptions, copts, nocopts):
  """
  Construct a set of compiler flags considering the input language,
  coding standard level, optional language features, and any
  changes requested by the author of the target
  """

  # RTT and exceptions must be controlled with the `exceptions` and
  # `rtti` keys instead of through copts and nocopts
  _check_copts_misuse("-frtti", "rtti", copts, nocopts)
  _check_copts_misuse("-fno-rtti", "rtti", copts, nocopts)
  _check_copts_misuse("-fexceptions", "exceptions", copts, nocopts)
  _check_copts_misuse("-fno-exceptions", "exceptions", copts, nocopts)

  # Pedanticness is controlled through the coding standard level, 
  # selected by the choice of target creation macro.
  if "-pedantic" in copts or "-pedantic" in nocopts:
    fail("Do not try to control pedantic by passing in copts or nocopts")

  cflags = _get_default_flags(lang, level)

  if lang == "c":
    if rtti:
      fail("Enabling RTTI is meaningless with C targets")
    if exceptions:
      fail("Enabling exceptions is meaningless with C targets")
  else:
    cflags += ["-frtti" if rtti else "-fno-rtti"]
    cflags += ["-fexceptions" if exceptions else "-fno-exceptions"]

  # Portable and safe targets may only add compiler options, not remove them
  if level in [PROD, PROD_PORTABLE, SAFE, SAFE_PORTABLE]:
    if len(nocopts) > 0:
      fail("Passing nocopts to production or safe targets is not allowed. Only adding flags via copts is permitted")

  # Try to catch anyone trying to skirt the above restriction by adding "-Wno-x"
  # which would be the same as passing "-Wx" in ncopts
  for f in copts:
    if f.startswith("-Wno-"):
      fail("Disabling warnings by passing -Wno-* via copts is not allowed. Use nocopts (only valid on internal level targets)")
    if f not in cflags:
      cflags += [f]

  cflags = [f for f in cflags if f not in nocopts]

  return select({
    Label("//cc:_disable_warnings_as_errors"): [],
    "//conditions:default": ["-Werror"],
  }) + select({
    Label("//cc/constraints:gcc-6"): [f for f in cflags if f not in GCC6_INCOMPATIBLE_FLAGS],
    Label("//cc/constraints:gcc-5"): [f for f in cflags if f not in GCC5_INCOMPATIBLE_FLAGS],
    "//conditions:default": cflags,
  })

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

# Handle various nuances of local include paths
def _construct_local_includes(local_includes):
    return [construct_local_include(path) for path in local_includes]

def _add_binary(**kwargs):
  """
  Add an executable target. Generic function to be called from a 
  wrapper macro which properly sets the coding standard level
  """

  level = kwargs.pop("level")

  lang = kwargs.pop("lang")

  if 'extensions' in kwargs and level in [PROD_PORTABLE, SAFE_PORTABLE]:
    fail("Compiler extensions may not be enabled on portable targets")

  if 'standard' in kwargs and level in [SAFE, SAFE_PORTABLE]:
    fail("Language standard may not be changed for safe targets")

  extensions = kwargs.pop("extensions", False)
  standard = kwargs.pop("standard", None)

  lang_flag = _get_lang_flag(lang, extensions, standard)

  copts = kwargs.pop("copts", [])
  nocopts = kwargs.pop("nocopts", [])

  rtti = kwargs.pop("rtti", False)
  exceptions = kwargs.pop("exceptions", False)

  local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

  cflags = lang_flag + local_includes + _construct_cflags(lang, level, rtti, exceptions, copts, nocopts)
  
  kwargs["copts"] = cflags

  _create_srcs(**kwargs)
  _create_hdrs(**kwargs)

  kwargs["tags"] = [BINARY, level] + kwargs.get("tags", [])

  native.cc_binary(**kwargs)

def _add_library(**kwargs):
  """
  Add a library target. Generic function to be called from a wrapper macro
  which properly sets the coding standard level
  """

  level = kwargs.pop("level")

  lang = kwargs.pop("lang")
  extensions = kwargs.pop("extensions", False)
  standard = kwargs.pop("standard", None)

  if extensions and level in [PROD_PORTABLE, SAFE_PORTABLE]:
    fail("Compiler extensions may not be enabled on portable targets")

  lang_flag = _get_lang_flag(lang, extensions, standard)

  copts = kwargs.pop("copts", [])
  nocopts = kwargs.pop("nocopts", [])

  rtti = kwargs.pop("rtti", False)
  exceptions = kwargs.pop("exceptions", False)

  local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

  cflags = lang_flag + local_includes + _construct_cflags(lang, level, rtti, exceptions, copts, nocopts)
  
  kwargs["copts"] = cflags

  _create_srcs(**kwargs)
  _create_hdrs(**kwargs)

  kwargs["tags"] = [LIBRARY, level] + kwargs.get("tags", [])

  native.cc_library(**kwargs)

def _add_test(**kwargs):
  """
  Add a test suite. To be called from the wrapper macro
  """

  if "level" in kwargs:
    fail("Coding Standard level can't be specified for tests, they are always internal")

  lang = kwargs.pop("lang")
  extensions = kwargs.pop("extensions", False)
  standard = kwargs.pop("standard", None)

  lang_flag = _get_lang_flag(lang, extensions, standard)

  copts = kwargs.pop("copts", [])
  nocopts = kwargs.pop("nocopts", [])
  nocopts.append("-Wdeprecated-declarations")
  #copts.append("-Wno-deprecated-declarations")

  # RTTI and Exceptions are enabled by default for tests
  rtti = kwargs.pop("rtti", True)
  exceptions = kwargs.pop("exceptions", True)

  local_includes = _construct_local_includes(kwargs.pop("local_includes", []))

  cflags = lang_flag + local_includes + _construct_cflags(lang, INTERNAL, rtti, exceptions, copts, nocopts) + ["-Wno-deprecated-declarations"]
  
  kwargs["copts"] = cflags

  _create_srcs(**kwargs)
  _create_hdrs(**kwargs)

  if "type" not in kwargs:
    fail("Type must be given for tests, either UNIT or INTEGRATION")

  type = kwargs.pop("type")
  if not (type == UNIT or type == INTEGRATION):
    fail("The 'type' attribute must be either UNIT or INTEGRATION")

  kwargs["tags"] = [BINARY, TEST, INTERNAL, type] + kwargs.get("tags", [])

  native.cc_test(**kwargs)


def _assert_no_reserved_keys(**kwargs):
  if 'lang' in kwargs:
    fail("Do not try to specify language manually")
  if 'level' in kwargs:
    fail("Do not try to specify coding standard manually")

def swift_internal_c_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "c", level = INTERNAL, **kwargs)

def swift_prod_c_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "c", level = PROD, **kwargs)

def swift_prod_portable_c_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "c", level = PROD_PORTABLE, **kwargs)

def swift_safe_c_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "c", level = SAFE, **kwargs)

def swift_safe_portable_c_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "c", level = SAFE_PORTABLE, **kwargs)

def swift_internal_c_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "c", level = INTERNAL, **kwargs)

def swift_prod_c_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "c", level = PROD, **kwargs)

def swift_prod_portable_c_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "c", level = PROD_PORTABLE, **kwargs)

def swift_safe_c_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "c", level = SAFE, **kwargs)

def swift_safe_portable_c_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "c", level = SAFE_PORTABLE, **kwargs)

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
  _add_binary(lang = "cc", level = PROD_PORTABLE, **kwargs)

def swift_safe_cc_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "cc", level = SAFE, **kwargs)

def swift_safe_portable_cc_binary(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_binary(lang = "cc", level = SAFE_PORTABLE, **kwargs)

def swift_internal_cc_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "cc", level = INTERNAL, **kwargs)

def swift_prod_cc_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "cc", level = PROD, **kwargs)

def swift_prod_portable_cc_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "cc", level = PROD_PORTABLE, **kwargs)

def swift_safe_cc_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "cc", level = SAFE, **kwargs)

def swift_safe_portable_cc_library(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  _add_library(lang = "cc", level = SAFE_PORTABLE, **kwargs)

def swift_new_cc_test(**kwargs):
  _assert_no_reserved_keys(**kwargs)
  # level doesn't need to be specified for tests, it's always INTERNAL
  _add_test(lang = "cc", **kwargs)

