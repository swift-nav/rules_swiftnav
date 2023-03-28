# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("//tools:configure_file.bzl", "configure_file_impl")

def _swift_doxygen_impl(ctx):
    vars = ctx.attr.vars | {}
    vars["DOXYGEN_SOURCE_DIRECTORIES"] = '" "'.join(ctx.attr.doxygen_source_directories)

    doxygen_out = ctx.actions.declare_directory(ctx.attr.doxygen_output_directory)
    vars["DOXYGEN_OUTPUT_DIRECTORY"] = doxygen_out.path

    config = configure_file_impl(ctx, vars, ctx.attr.doxygen_output_directory + "_Doxyfile")[0].files.to_list()[0]

    ctx.actions.run_shell(
        inputs = [config] + ctx.files.deps,
        outputs = [doxygen_out],
        command = """
        DOXYGEN_DOT_FOUND=NO
        DOXYGEN_DOT_PATH=

        if command -v dot &> /dev/null
        then
            DOXYGEN_DOT_FOUND=YES
            DOXYGEN_DOT_PATH=$(which dot)
        fi

        sed -i "s|@DOXYGEN_DOT_FOUND@|$DOXYGEN_DOT_FOUND|g" {config}
        sed -i "s|@DOXYGEN_DOT_PATH@|$DOXYGEN_DOT_PATH|g" {config}
        sed -i "s|@PLANTUML_JAR_PATH@|/usr/local/bin/plantuml.jar|g" {config}

        doxygen {config}
        """.format(config = config.path),
    )

    return [DefaultInfo(files = depset([doxygen_out, config]))]

_swift_doxygen = rule(
    implementation = _swift_doxygen_impl,
    attrs = {
        "vars": attr.string_dict(),
        "template": attr.label(
            allow_single_file = [".in"],
            mandatory = True,
        ),
        "deps": attr.label_list(),
        "doxygen_source_directories": attr.string_list(),
        "doxygen_output_directory": attr.string(),
    },
)

def swift_doxygen(**kwargs):
    kwargs["tags"] = ["manual"] + kwargs.get("tags", [])

    _swift_doxygen(**kwargs)
