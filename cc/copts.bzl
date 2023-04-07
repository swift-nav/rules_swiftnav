# The following are set by default by Bazel:
# -Wall, -Wunused-but-set-parameter, -Wno-free-heap-object
DEFAULT_COPTS = [
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

GCC6_DISABLED_COPTS = ["-Wimplicit-fallthrough"]
GCC6_COPTS = [copt for copt in DEFAULT_COPTS if copt not in GCC6_DISABLED_COPTS]
GCC5_COPTS = GCC6_COPTS
