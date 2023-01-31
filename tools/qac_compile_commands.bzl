# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("//tools:gen_sonar_cfg.bzl", "FilesInfo", "get_target_files")

def qac_compile_commands(name, tool, **kwargs):
    """Replaces -isystem with -I in a compile_commands.json file.

    This is necessary to get Helix QAC to work correctly.

    Args:
        name: A unique label for this rule.
        tool: A label refrencing a @hedron_compile_commands:refresh_compile_commands target.

    """
    arg = "$(location {})".format(tool)
    native.sh_binary(
        name = name,
        srcs = [Label("//tools:qac_compile_commands.sh")],
        args = [arg],
        data = [tool],
        **kwargs
    )

def _run_qac_impl(ctx):
    out = ctx.actions.declare_directory("qac-projects")

    target_files = []

    for target in ctx.attr.targets:
        target_files.extend(target[FilesInfo].files)

    ctx.actions.run_shell(
        inputs = target_files +
                 ctx.files.test_srcs +
                 ctx.files.compile_commands +
                 ctx.files.qac_config,
        outputs = [out],
        command = """
        set -ex

        export GIT_TAG=dummy
        export QAC_PROJECT_NAME={qac_project_name}
        export QAC_PROJECTS_ROOT_DIR={qac_project_dir}
        export QAC_RCF_PATH={qac_config}
        export COMPILE_COMMANDS_PATH={compile_commands}

        PATH=$PATH:/opt/Perforce/Helix-QAC-2020.1/common/bin
        HOME=$PWD PATH=$PATH qac || true
        """.format(
            compile_commands = ctx.files.compile_commands[0].path,
            qac_project_dir = out.path,
            qac_config = ctx.files.qac_config[0].path,
            qac_project_name = ctx.attr.qac_project_name,
        ),
    )

    return [DefaultInfo(files = depset([out]))]

run_qac = rule(
    implementation = _run_qac_impl,
    attrs = {
        "targets": attr.label_list(aspects = [get_target_files]),
        "test_srcs": attr.label_list(),
        "compile_commands": attr.label(),
        "qac_config": attr.label(),
        "qac_project_name": attr.string(),
    },
)
