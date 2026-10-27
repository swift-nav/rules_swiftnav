# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("//tools:configure_file.bzl", "configure_file_impl")

def _swift_doxygen_impl(ctx):
    vars = ctx.attr.vars | {}  # copy dict instead of referencing it
    vars["DOXYGEN_SOURCE_DIRECTORIES"] = '" "'.join(ctx.attr.doxygen_source_directories)

    doxygen_out = ctx.actions.declare_directory(ctx.attr.name + "_doxygen")
    vars["DOXYGEN_OUTPUT_DIRECTORY"] = doxygen_out.path

    # this performs a CMake-like replacement of @VAR@ based on the vars dict
    config = configure_file_impl(ctx, vars, ctx.attr.name + "_Doxyfile")[0].files.to_list()[0]

    # ctx.info_file is bazel-out/stable-status.txt, populated by --workspace_status_command
    # when --stamp is enabled. Contains STABLE_GIT_TAG and other workspace status values.
    info_file = ctx.info_file

    doxygen_bin = ctx.file._doxygen

    ctx.actions.run_shell(
        inputs = [config, info_file] + ctx.files.deps,
        tools = [doxygen_bin],
        outputs = [doxygen_out],
        env = vars,
        command = """
        DOXYGEN_DOT_FOUND=NO
        DOXYGEN_DOT_PATH=
        if command -v dot &> /dev/null
        then
            DOXYGEN_DOT_FOUND=YES
            DOXYGEN_DOT_PATH=$(which dot)
        fi

        EXEC_ROOT=$(pwd)

        # Use the GIT TAG
        STABLE_GIT_TAG=$(grep -m1 '^STABLE_GIT_TAG ' {info_file} | cut -d' ' -f2-)

        # Apply backward compatibility sed replacements into a temp file within
        # this sandbox so all $EXEC_ROOT-expanded paths point to the correct location.
        sed "s|@DOXYGEN_DOT_FOUND@|$DOXYGEN_DOT_FOUND|g" {original_config} | \
        sed "s|@DOXYGEN_DOT_PATH@|$DOXYGEN_DOT_PATH|g" | \
        sed "s|@PLANTUML_JAR_PATH@|/usr/local/bin/plantuml.jar|g" | \
        sed "s|@INPUT_DIR@|$PROJECT_SOURCE_DIR|g" | \
        sed "s|@PROJECT_NAME@|$PROJECT_NAME|g" | \
        sed "s|@STABLE_GIT_TAG@|$STABLE_GIT_TAG|g" | \
        sed "s|@DOXYGEN_EXCLUDE@|$DOXYGEN_EXCLUDE|g" | \
        sed "s|@PROJECT_SOURCE_DIR@|$EXEC_ROOT|g" > _processed_Doxyfile

        "$EXEC_ROOT/{doxygen_bin}" _processed_Doxyfile
        """.format(
            original_config = config.path,
            info_file = info_file.path,
            doxygen_bin = doxygen_bin.path,
        ),
    )

    # The generated Doxyfile is only exposed via an output group, so that it
    # does not end up in packaged documentation
    return [
        DefaultInfo(files = depset([doxygen_out])),
        OutputGroupInfo(doxyfile = depset([config])),
    ]

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
        "_doxygen": attr.label(
            default = "@rules_swiftnav//doxygen:doxygen",
            allow_single_file = True,
            cfg = "exec",
        ),
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

def _doc_zip_impl(ctx):
    html_dir = ctx.file.html
    zipper = ctx.executable._zipper
    info_file = ctx.info_file

    ctx.actions.run_shell(
        inputs = [html_dir, info_file],
        tools = [zipper],
        outputs = [ctx.outputs.out],
        command = """
        set -euo pipefail

        # ctx.info_file is bazel-out/stable-status.txt, populated by
        # --workspace_status_command when --stamp is enabled
        VERSION=$(grep -m1 '^STABLE_GIT_VERSION ' {info_file} | cut -d' ' -f2- || true)
        PREFIX="${{VERSION:-unversioned}}-{package_name}"

        ARGS=$(mktemp)
        find -L {html_dir} -type f | LC_ALL=C sort | while IFS= read -r FILE; do
            echo "$PREFIX/html/${{FILE#{html_dir}/}}=$FILE"
        done > "$ARGS"

        {zipper} cC {out} "@$ARGS"
        rm -f "$ARGS"
        """.format(
            info_file = info_file.path,
            package_name = ctx.attr.package_name,
            html_dir = html_dir.path,
            zipper = zipper.path,
            out = ctx.outputs.out.path,
        ),
    )

    return DefaultInfo(files = depset([ctx.outputs.out]))

_doc_zip = rule(
    implementation = _doc_zip_impl,
    attrs = {
        "html": attr.label(
            allow_single_file = True,
            mandatory = True,
        ),
        "package_name": attr.string(mandatory = True),
        "out": attr.output(mandatory = True),
        "_zipper": attr.label(
            default = "@bazel_tools//tools/zip:zipper",
            executable = True,
            cfg = "exec",
        ),
    },
)

def swift_doxygen(package_name = None, **kwargs):
    """Generates Doxygen HTML documentation and a zip package of it.

    The zip package contains a single top-level folder
    `<version>-<package_name>/html/`, where `<version>` is STABLE_GIT_VERSION
    (or `unversioned` when not stamping), so that multiple packages and
    versions can be extracted side by side.

    Args:
        package_name: name of the documentation package, defaults to `name`
        **kwargs: arguments passed on to the Doxygen rule
    """
    tags = ["manual"] + kwargs.get("tags", [])
    name = kwargs["name"]
    name_html = name + "_html"
    name_zip = name + "_zip"
    package_name = package_name or name

    kwargs["tags"] = tags

    _swift_doxygen(**kwargs)

    _filter_html(
        name = name_html,
        tags = tags,
        srcs = [name],
        html_path = name + "_doxygen/html",
    )

    _doc_zip(
        name = name_zip,
        tags = tags,
        html = name_html,
        package_name = package_name,
        out = package_name + ".zip",
    )
