def _stamp_file_impl(ctx):
    status_file = ctx.info_file
    defaults = json.encode(ctx.attr.defaults)
    template = ctx.file.template
    out = ctx.actions.declare_file(ctx.attr.out)

    args = ctx.actions.args()
    args.add(status_file)
    args.add(defaults)
    args.add(template)
    args.add(out)

    ctx.actions.run(
        inputs = [status_file, template],
        executable = ctx.executable.exec,
        arguments = [args],
        outputs = [out],
    )

    return [DefaultInfo(files = depset([out]))]

stamp_file = rule(
    implementation = _stamp_file_impl,
    attrs = {
        "out": attr.string(mandatory = True),
        "template": attr.label(
            allow_single_file = [".in"],
            mandatory = True,
        ),
        "defaults": attr.string_dict(
            mandatory = True,
        ),
        "exec": attr.label(
            executable = True,
            cfg = "exec",
            allow_files = True,
            default = "//stamp:stamp_file",
        ),
    },
)
