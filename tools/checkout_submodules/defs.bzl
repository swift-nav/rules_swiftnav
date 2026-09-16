# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Generate the CI submodule-checkout script and keep the checked-in copy in sync."""

load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

def _generate_init_script_impl(ctx):
    args = ctx.actions.args()
    args.add("--module-file", ctx.file.module_file)
    args.add("--output", ctx.outputs.out)
    args.add_all(ctx.attr.extra_paths, before_each = "--extra-path")
    args.add("--update-target", ctx.attr.update_target)

    ctx.actions.run(
        executable = ctx.executable._generator,
        arguments = [args],
        inputs = [ctx.file.module_file],
        outputs = [ctx.outputs.out],
        mnemonic = "GenSubmoduleCheckout",
        progress_message = "Generating %s" % ctx.outputs.out.short_path,
    )

generate_init_script = rule(
    implementation = _generate_init_script_impl,
    attrs = {
        "extra_paths": attr.string_list(
            doc = "Submodule paths to initialize that MODULE.bazel does not declare.",
        ),
        "module_file": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "MODULE.bazel to read the local_path_override paths from.",
        ),
        "out": attr.output(mandatory = True),
        "update_target": attr.string(
            mandatory = True,
            doc = "Label of the update target, printed in the generated script header.",
        ),
        "_generator": attr.label(
            default = Label(":generate_init_script"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def checkout_submodules_script(name, script, module_file, extra_paths = [], **kwargs):
    """Keeps `script` in sync with the submodule set MODULE.bazel declares.

    Creates `<name>.update_test`, which fails if the checked-in script differs
    from the generated one, and `<name>.update`, which overwrites `script`.

    Args:
        name: Base target name.
        script: Label of the checked-in script, an exported source file.
        module_file: Label of the MODULE.bazel to derive the submodule set from.
        extra_paths: Submodule paths that MODULE.bazel does not declare.
        **kwargs: Passed to the test target.
    """
    update = "{}.update".format(name)
    update_target = "//{}:{}".format(native.package_name(), update)
    generated = "_{}.sh".format(name)

    generate_init_script(
        name = name,
        out = generated,
        module_file = module_file,
        extra_paths = extra_paths,
        update_target = update_target,
    )

    diff_test(
        name = "{}_test".format(update),
        file1 = script,
        file2 = generated,
        failure_message = "{} is out of sync with {}. Run 'bazel run {}'.".format(
            script,
            module_file,
            update_target,
        ),
        **kwargs
    )

    sh_binary(
        name = update,
        srcs = [Label(":update.sh")],
        args = ["$(rootpath {})".format(generated), "$(rootpath {})".format(script)],
        data = [generated, script],
        tags = ["manual"],
    )
