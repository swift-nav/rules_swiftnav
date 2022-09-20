def swift_get_compile_options(
        exceptions = None,
        rtti = None,
        warning = None,
        add_compile_options = None,
        remove_compile_options = None,
        cxx_standard = None,
        c_standard = None):
    if add_compile_options == None:
        add_compile_options = []
    if remove_compile_options == None:
        remove_compile_options = []

    for flag in add_compile_options + remove_compile_options:
        if flag == "-fexceptions":
            fail("Do not specify -fexceptions directly, use 'exceptions' argument instead")
        if flag == "-fno-exceptions":
            fail("Do not specify -fno-exceptions directly, avoid 'exceptions' argument instead")
        if flag == "-frtti":
            fail("Do not specify -frtti directly, use 'rtti' argument instead")
        if flag == "-fno-rtti":
            fail("Do not specify -fno-rtti directly, avoid 'rtti' argument instead")
        if flag == "-Wno-error":
            fail("Do not specify -Wno-error directly, use 'warning' to disable -Werror")

    all_flags = []

    # if not warning:
    #     all_flags += ["-Werror", "-Wno-error=deprecated-declarations"]

    # '-Wall' '-Wunused-but-set-parameter' '-Wno-free-nonheap-object' flags are set by default by bazel
    all_flags += [
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
        "-Wmissing-include-dirs",
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
    ]

    if remove_compile_options:
        for flag in remove_compile_options:
            if not flag in all_flags:
                fail("Compiler flag '%s' specified for removal is not part of the set of common compiler flags" % flag)
            all_flags.remove(flag)

    all_flags += add_compile_options

    if exceptions:
        all_flags.append("-fexceptions")
    else:
        all_flags.append("-fno-exceptions")

    if rtti:
        all_flags.append("-frtti")
    else:
        all_flags.append("-fno-rtti")

    if cxx_standard:
        all_flags.append("-std=c++" + cxx_standard)
    else:
        all_flags.append("-std=c++14")

    if c_standard:
        all_flags.append("-std=c" + c_standard)
    else:
        all_flags.append("-std=c99")

    return all_flags

def swift_cc_library(
        name,
        srcs = None,
        hdrs = None,
        includes = None,
        textual_hdrs = None,
        visibility = None,
        deps = None,
        add_compile_options = None,
        remove_compile_options = None,
        cxx_standard = None,
        c_standard = None):
    if add_compile_options == None:
        add_compile_options = []
    add_compile_options.append("-pedantic")
    copts = swift_get_compile_options(
        add_compile_options = add_compile_options,
        remove_compile_options = remove_compile_options,
        cxx_standard = cxx_standard,
        c_standard = c_standard,
    )
    native.cc_library(
        name = name,
        srcs = srcs,
        hdrs = hdrs,
        copts = copts,
        deps = deps,
        visibility = visibility,
        includes = includes,
        textual_hdrs = textual_hdrs,
    )

def swift_cc_tool_library(
        name,
        srcs = None,
        hdrs = None,
        includes = None,
        textual_hdrs = None,
        visibility = None,
        deps = None,
        add_compile_options = None,
        remove_compile_options = None,
        cxx_standard = None,
        c_standard = None):
    copts = swift_get_compile_options(
        add_compile_options = add_compile_options,
        remove_compile_options = remove_compile_options,
        cxx_standard = cxx_standard,
        c_standard = c_standard,
    )
    native.cc_library(
        name = name,
        srcs = srcs,
        hdrs = hdrs,
        copts = copts,
        deps = deps,
        visibility = visibility,
        includes = includes,
        textual_hdrs = textual_hdrs,
    )

def swift_cc_binary(
        name,
        srcs = None,
        hdrs = None,
        includes = None,
        visibility = None,
        deps = None,
        add_compile_options = None,
        remove_compile_options = None,
        cxx_standard = None,
        c_standard = None):
    if add_compile_options == None:
        add_compile_options = []
    add_compile_options.append("-pedantic")
    copts = swift_get_compile_options(
        add_compile_options = add_compile_options,
        remove_compile_options = remove_compile_options,
        cxx_standard = cxx_standard,
        c_standard = c_standard,
    )
    native.cc_binary(
        name = name,
        srcs = srcs,
        hdrs = hdrs,
        copts = copts,
        deps = deps,
        visibility = visibility,
        includes = includes,
    )

def swift_cc_tool(
        name,
        srcs = None,
        hdrs = None,
        includes = None,
        visibility = None,
        deps = None,
        add_compile_options = None,
        remove_compile_options = None,
        cxx_standard = None,
        c_standard = None):
    copts = swift_get_compile_options(
        add_compile_options = add_compile_options,
        remove_compile_options = remove_compile_options,
        cxx_standard = cxx_standard,
        c_standard = c_standard,
    )
    native.cc_binary(
        name = name,
        srcs = srcs,
        hdrs = hdrs,
        copts = copts,
        includes = includes,
        visibility = visibility,
        deps = deps,
    )

def swift_cc_test(
        name,
        srcs = None,
        hdrs = None,
        data = None,
        includes = None,
        visibility = None,
        deps = None,
        add_compile_options = None,
        remove_compile_options = None,
        cxx_standard = None,
        c_standard = None):
    copts = swift_get_compile_options(
        add_compile_options = add_compile_options,
        remove_compile_options = remove_compile_options,
        cxx_standard = cxx_standard,
        c_standard = c_standard,
    )
    native.cc_test(
        name = name,
        srcs = srcs,
        hdrs = hdrs,
        copts = copts,
        data = data,
        includes = includes,
        visibility = visibility,
        deps = deps,
    )
