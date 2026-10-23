# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Generate the LFS lockfile that the `lfs` module extension reads and keep it in sync."""

load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

def _file_args(f):
    return ["--file", f.path, f.short_path]

def _generate_lockfile_impl(ctx):
    args = ctx.actions.args()
    args.use_param_file("@%s")
    args.set_param_file_format("multiline")
    args.add("--gitattributes", ctx.file.gitattributes)
    args.add("--output", ctx.outputs.out)
    args.add_all(ctx.files.srcs, map_each = _file_args)

    ctx.actions.run(
        executable = ctx.executable._generator,
        arguments = [args],
        inputs = ctx.files.srcs + [ctx.file.gitattributes],
        outputs = [ctx.outputs.out],
        mnemonic = "GenLfsLockfile",
        progress_message = "Generating %s" % ctx.outputs.out.short_path,
    )

generate_lockfile = rule(
    implementation = _generate_lockfile_impl,
    attrs = {
        "gitattributes": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "Root .gitattributes that marks files as LFS-tracked.",
        ),
        "out": attr.output(mandatory = True),
        "srcs": attr.label_list(
            allow_files = True,
            doc = "Candidate files; the ones .gitattributes tracks with LFS go into the lockfile.",
        ),
        "_generator": attr.label(
            default = Label(":generate_lockfile"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def lfs_lockfile(name, lockfile, srcs, gitattributes = "//:.gitattributes", **kwargs):
    """Keeps `lockfile` in sync with the LFS-tracked files among `srcs`.

    The lockfile maps workspace paths to LFS oids and is the input of the `lfs`
    module extension. Pointers and pulled files yield the same oid, so the
    lockfile does not depend on whether `git lfs pull` ran.

    Creates `<name>.update_test`, which fails if the checked-in lockfile differs
    from the generated one, and `<name>.update`, which overwrites `lockfile`.

    Args:
        name: Base target name.
        lockfile: Label of the checked-in JSON lockfile, an exported source file.
        srcs: Candidate files, e.g. filegroups or exported files from several packages.
        gitattributes: Label of the root .gitattributes.
        **kwargs: Passed to the test target.
    """
    update = "{}.update".format(name)
    generated = "_{}.json".format(name)

    generate_lockfile(
        name = name,
        out = generated,
        srcs = srcs,
        gitattributes = gitattributes,
    )

    diff_test(
        name = "{}_test".format(update),
        file1 = lockfile,
        file2 = generated,
        failure_message = "{} is out of sync with the LFS files. Run 'bazel run //{}:{}'.".format(
            lockfile,
            native.package_name(),
            update,
        ),
        **kwargs
    )

    sh_binary(
        name = update,
        srcs = [Label("//tools/checkout_submodules:update.sh")],
        args = ["$(rootpath {})".format(generated), "$(rootpath {})".format(lockfile)],
        data = [generated, lockfile],
        tags = ["manual"],
    )
