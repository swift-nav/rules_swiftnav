# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

CMAKE_FALSE_CONSTANTS = ["0", "OFF", "NO", "FALSE", "N", "IGNORE", "NOTFOUND"]

def configure_file_impl(ctx, vars):
    subs = {}
    for (key, val) in vars.items():
        cmake_define_nl = "#cmakedefine {}\n".format(key)
        define_nl = "// #undef {}\n".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {}\n".format(key)
        cmake_define_s = "#cmakedefine {} ".format(key)
        define_s = "// #undef {} ".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {} ".format(key)

        cmake_define_01_nl = "#cmakedefine01 {}\n".format(key)
        define_01_nl = "#define {} 0\n".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {} 1\n".format(key)
        cmake_define_01_s = "#cmakedefine01 {} ".format(key)
        define_01_s = "#define {} 0 ".format(key) if val in CMAKE_FALSE_CONSTANTS else "#define {} 1 ".format(key)

        subs[cmake_define_nl] = define_nl
        subs[cmake_define_s] = define_s
        subs[cmake_define_01_nl] = define_01_nl
        subs[cmake_define_01_s] = define_01_s

        subs["@{}@".format(key)] = val
        subs["${" + key + "}"] = val

    out = ctx.actions.declare_file(ctx.attr.out)
    ctx.actions.expand_template(
        output = out,
        template = ctx.file.template,
        substitutions = subs,
    )
    return [DefaultInfo(files = depset([out]))]

def _configure_file_impl(ctx):
    return configure_file_impl(ctx, ctx.attr.vars)

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
