_internal_coding_standard_flags = {
    "common": [
        "-Waddress",
        "-Warray-bounds",
        "-Wbool-compare",
        "-Wbool-operation",
        "-Wcast-function-type",
        "-Wchar-subscripts",
        "-Wdangling-else",
        "-Wignored-qualifiers",
        "-Winit-self",
        "-Winvalid-pch",
        "-Wlogical-not-parentheses",
        "-Wmaybe-uninitialized",
        "-Wmemset-elt-size",
        "-Wmemset-transposed-args",
        "-Wmisleading-indentation",
        "-Wmismatched-dealloc",
        "-Wmissing-attributes",
        "-Wmissing-field-initializers",
        "-Wmultistatement-macros",
        "-Wparentheses",
        "-Wrestrict",
        "-Wsequence-point",
        "-Wshift-negative-value",
        "-Wsizeof-array-div",
        "-Wsizeof-pointer-div",
        "-Wsizeof-pointer-memaccess",
        "-Wstring-compare",
        "-Wtrigraphs",
        "-Wtype-limits",
        "-Wuninitialized",
        "-Wunknown-pragmas",
        "-Wwrite-strings",
        "-Wno-error=deprecated-declarations",
        "-Wno-tautological-unsigned-zero-compare",
        "-Wno-stack-protector",
    ],
    "c": [],
    "cxx": [],
}

_prod_coding_standard_flags = {
    "common": _internal_coding_standard_flags["common"]
    + [
        "-Wall",
        "-Wextra",
        "-Wcast-qual",
        "-Wcomment",
        "-Wclobbered",
        "-Wconversion",
        "-Wdisabled-optimization",
        "-Wempty-body",
        "-Wenum-compare",
        "-Wfloat-equal",
        "-Wenum-conversion",
        "-Wenum-int-mismatch",
        "-Wfloat-conversion",
        "-Wformat",
        "-Wformat-extra-args",
        "-Wformat-overflow",
        "-Wformat-security",
        "-Wformat-truncation",
        "-Wformat-y2k",
        "-Wimplicit-fallthrough",
        "-Wimport",
        "-Wint-in-bool-context",
        "-Wmissing-braces",
        "-Wnarrowing",
        "-Wnonnull",
        "-Wnonnull-compare",
        "-Wopenmp-simd",
        "-Wredundant-decls",
        "-Wreturn-type",
        "-Wself-move",
        "-Wshadow",
        "-Wsign-compare",
        "-Wsign-conversion",
        "-Wstrict-aliasing",
        "-Wstrict-overflow=1",
        "-Wswitch",
        "-Wswitch-default",
        "-Wswitch-enum",
        "-Wtautological-compare",
        "-Wtautological-unsigned-zero-compare",
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
    "c": _internal_coding_standard_flags["c"] + [],
    "cxx": _internal_coding_standard_flags["cxx"] + [],
}

_safe_coding_standard_flags = {
    "common": _prod_coding_standard_flags["common"]
    + [
        "-Wpointer-arith",
    ],
    "c": _prod_coding_standard_flags["c"] + [],
    "cxx": _prod_coding_standard_flags["cxx"] + [],
}

_portable_coding_standard_flags = [
    "-pedantic",
]

disable_conversion_warning_flags = [
    "-Wno-conversion",
    "-Wno-float-conversion",
    "-Wno-sign-conversion",
    "-Wno-implicit-int-conversion",
    "-Wno-implicit-int-float-conversion",
    "-Wno-shorten-64-to-32",
]

disable_warnings_for_test_targets_flags = [
  "-Wno-unused",
] + disable_conversion_warning_flags


def filter_flags(flags, invalid_flags):
    return [f for f in flags if f not in invalid_flags]


def get_flags_for_lang_and_level(lang, level, invalid_flags=[], extra_flags=[]):
    if level == "internal":
        flags = _internal_coding_standard_flags
    elif level == "prod":
        flags = _prod_coding_standard_flags
    elif level == "safe":
        flags = _safe_coding_standard_flags
    else:
        fail

    flags = flags["common"] + flags[lang] + extra_flags

    return filter_flags(flags, invalid_flags)
