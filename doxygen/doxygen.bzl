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
load("@rules_pkg//pkg:pkg.bzl", "pkg_zip")

def _swift_doxygen_impl(ctx):
    vars = ctx.attr.vars | {}  # copy dict instead of referencing it
    vars["DOXYGEN_SOURCE_DIRECTORIES"] = '" "'.join(ctx.attr.doxygen_source_directories)

    doxygen_out = ctx.actions.declare_directory(ctx.attr.name + "_doxygen")
    vars["DOXYGEN_OUTPUT_DIRECTORY"] = doxygen_out.path

    config = configure_file_impl(ctx, vars, ctx.attr.name + "_Doxyfile")[0].files.to_list()[0]

    input_dir = ""
    if "PROJECT_SOURCE_DIR" in vars:
        input_dir = vars["PROJECT_SOURCE_DIR"]

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
        sed -i "s|@INPUT_DIR@|{input_dir}|g" {config}

        PATH=$PATH doxygen {config}
        """.format(config = config.path, input_dir = input_dir),
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
    },
)

def _filter_html_impl(ctx):
    out = ctx.actions.declare_directory(ctx.attr.name)
    ctx.actions.run_shell(
        outputs = [out],
        inputs = ctx.files.srcs,
        command = """
            cp -r $(find . -type d -regex ".*{html_path}")/* {out}
        """.format(out = out.path, html_path = ctx.attr.html_path),
    )
    return DefaultInfo(files = depset([out]))

_filter_html = rule(
    implementation = _filter_html_impl,
    attrs = {
        "srcs": attr.label_list(mandatory = True),
        "html_path": attr.string(mandatory = True),
    },
)

def swift_doxygen(**kwargs):
    tags = ["manual"] + kwargs.get("tags", [])
    name = kwargs["name"]
    name_html = name + "_html"
    name_zip = name + "_zip"

    kwargs["tags"] = tags

    _swift_doxygen(**kwargs)

    _filter_html(
        name = name_html,
        tags = tags,
        srcs = [name],
        html_path = name + "_doxygen/html",
    )

    pkg_zip(
        name = name_zip,
        srcs = [name_html],
        tags = tags,
        package_file_name = name + ".zip",
        strip_prefix = name_html,
    )
