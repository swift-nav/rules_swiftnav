CMAKE_FALSE_CONSTANTS = ["0", "OFF", "NO", "FALSE", "N", "IGNORE", "NOTFOUND"]

def _configure_file_impl(ctx):
    vars = {}
    for (key, val) in ctx.attr.vars.items():
        cmake_define_nl = "#cmakedefine {}\n".format(key)
        define_nl = "// #undef {}\n".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {}\n".format(key)
        cmake_define_s = "#cmakedefine {} ".format(key)
        define_s = "// #undef {} ".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {} ".format(key)

        cmake_define_01_nl = "#cmakedefine01 {}\n".format(key)
        define_01_nl = "#define {} 0\n".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {} 1\n".format(key)
        cmake_define_01_s = "#cmakedefine01 {} ".format(key)
        define_01_s = "#define {} 0 ".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {} 1 ".format(key)

        vars[cmake_define_nl] = define_nl
        vars[cmake_define_s] = define_s
        vars[cmake_define_01_nl] = define_01_nl
        vars[cmake_define_01_s] = define_01_s

        vars["@{}@".format(key)] = val
        vars["${" + key + "}"] = val

    out = ctx.actions.declare_file(ctx.attr.out)
    ctx.actions.expand_template(
        output = out,
        template = ctx.file.template,
        substitutions = vars,
    )
    return [DefaultInfo(files = depset([out]))]

configure_file = rule(
    implementation = _configure_file_impl,
    attrs = {
        "vars": attr.string_dict(),
        "out": attr.string(),
        "template": attr.label(
            allow_single_file = [".in"],
            mandatory = True,
        ),
    },
)
