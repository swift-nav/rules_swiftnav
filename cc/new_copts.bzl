INTERNAL_COPTS = [
    "-Wcast-align",
    "-Wcast-qual",
    "-Wchar-subscripts",
    "-Wcomment",
    "-Wdisabled-optimization",
    "-Wfloat-equal",
    "-Wformat",
    "-Wformat-security",
    "-Wformat-y2k",
    "-Wimport",
    "-Winit-self",
    "-Winvalid-pch",
    "-Wmissing-braces",
    "-Wmissing-field-initializers",
    "-Wparentheses",
    "-Wredundant-decls",
    "-Wreturn-type",
    "-Wsequence-point",
    "-Wshadow",
    "-Wswitch",
    "-Wswitch-default",
    "-Wswitch-enum",
    "-Wtrigraphs",
    "-Wuninitialized",
    "-Wunknown-pragmas",
    "-Wvolatile-register-var",
    "-Wwrite-strings",
    "-Wno-error=deprecated-declarations",
]

PORTABLE_COPTS = [
    "-pedantic",
    "-Wsign-compare",
    "-Wconversion",
    "-Wstack-protector",
    "-Wimplicit-fallthrough",
    "-Wunreachable-code",
    "-Wunused",
    "-Wunused-function",
    "-Wunused-label",
    "-Wunused-parameter",
    "-Wunused-value",
    "-Wunused-variable",
]

PROD_COPTS = [
    "-Wsign-compare",
    "-Wconversion",
    "-Wstack-protector",
    "-Wimplicit-fallthrough",
    "-Wunreachable-code",
    "-Wunused",
    "-Wunused-function",
    "-Wunused-label",
    "-Wunused-parameter",
    "-Wunused-value",
    "-Wunused-variable",
]

SAFE_COPTS = [
    "-Wpointer-arith",
]

COMMON_COPTS = {}
COMMON_COPTS["internal"] = INTERNAL_COPTS
COMMON_COPTS["prod"] = INTERNAL_COPTS + PROD_COPTS
COMMON_COPTS["portable"] = INTERNAL_COPTS + PORTABLE_COPTS
COMMON_COPTS["safe"] = INTERNAL_COPTS + PORTABLE_COPTS + SAFE_COPTS

GCC6_DISABLED_COPTS = ["-Wimplicit-fallthrough"]
GCC5_DISABLED_COPTS = GCC6_DISABLED_COPTS

def get_common_cc_opts(level, copts, nocopts):
  print(level)
  print(copts)
  print(nocopts)
  opts = COMMON_COPTS[level] + copts

  filtered_opts = [opt for opt in opts if opt not in nocopts]
  print(filtered_opts)

  return select({
    Label("//cc:_disable_warnings_as_errors"): [],
    "//conditions:default": ["-Werror"],
  }) + select({
    Label("//cc/constraints:gcc-6"): [copt for copt in filtered_opts if copt not in GCC6_DISABLED_COPTS],
    Label("//cc/constraints:gcc-5"): [copt for copt in filtered_opts if copt not in GCC5_DISABLED_COPTS],
    "//conditions:default": filtered_opts,
  })
