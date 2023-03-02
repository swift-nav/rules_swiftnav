def _stamping_impl(ctx):
    file = ctx.version_file

    print(ctx.version_file)

    tpl = ctx.file.template
    out = ctx.actions.declare_file(ctx.attr.out)

    args = ctx.actions.args()
    args.add(file)
    args.add(tpl)
    args.add(out)

    ctx.actions.run(
        inputs = [file, tpl],
        executable = ctx.executable.exec,
        arguments = [args],
        outputs = [out],
    )

    return [DefaultInfo(files = depset([out]))]

stamping = rule(
    implementation = _stamping_impl,
    attrs = {
        "out": attr.string(),
        "template": attr.label(
            allow_single_file = [".in"],
            mandatory = True,
        ),
        "exec": attr.label(
            executable = True,
            cfg = "exec",
            allow_files = True,
            default = "//stamping:stamping.py",
        ),
    },
)
