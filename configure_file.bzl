CMAKE_FALSE_CONSTANTS = ["0", "OFF", "NO", "FALSE", "N", "IGNORE", "NOTFOUND"]

def _configure_file_impl(ctx):
    vars = {}
    for (key, val) in ctx.attr.vars.items():
        cmake_define = "#cmakedefine {}".format(key)
        define = "// #undef {}".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {}".format(key)

        vars[cmake_define] = define
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
    doc = """
Equivalent of CMake's configure_file

Example:
  ```starlark
  configure_file(
      name = "config",
      out = "config.h",
      template = "config.h.in",
      vars = { "FOO":"BAR" }
  )
  ```
""",
    attrs = {
        "vars": attr.string_dict(
            doc = "Key values pairs to substitute.",
        ),
        "out": attr.string(
            doc = "Name of the generated file.",
        ),
        "template": attr.label(
            doc = "CMake style input template.",
            allow_single_file = [".in"],
            mandatory = True,
        ),
    },
)
