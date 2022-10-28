load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

CMAKE_FALSE_CONSTANTS = ["0", "OFF", "NO", "FALSE", "N", "IGNORE", "NOTFOUND"]

def _configure_file_impl(ctx):
    vars = {}
    for var in ctx.attr.vars:
        key_val = var.split("=")
        if len(key_val) != 2:
            # skip if var is not in the right format: <key>=<value>
            continue
        key = key_val[0]
        val = key_val[1]

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
    attrs = {
        "vars": attr.string_list(),
        "out": attr.string(),
        "template": attr.label(
            allow_single_file = [".in"],
            mandatory = True,
        ),
    },
)

def config_var(var, config):
    return select({
        config: [var + "=ON"],
        "//conditions:default": [var + "=OFF"],
    })

def var(var, value):
    return [var + "=" + value]

def config_flag(config, flag):
    string_flag(
        name = flag,
        build_setting_default = "",
    )

    native.config_setting(
        name = config,
        flag_values = {":" + flag: "ON"},
    )
