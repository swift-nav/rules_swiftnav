load("//cc:defs.bzl", "swift_cc_library")

def _stamping_impl(ctx):
    status_file = ctx.info_file
    template = ctx.file.template
    out = ctx.actions.declare_file(ctx.attr.out)

    args = ctx.actions.args()
    args.add(status_file)
    args.add(template)
    args.add(out)

    ctx.actions.run(
        inputs = [status_file, template],
        executable = ctx.executable.exec,
        arguments = [args],
        outputs = [out],
    )

    return [DefaultInfo(files = depset([out]))]

_stamping = rule(
    implementation = _stamping_impl,
    attrs = {
        "out": attr.string(mandatory = True),
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

def stamping(name, out, template, hdrs, includes):
    source_name = name + "_"

    _stamping(name = source_name, out = out, template = template)

    swift_cc_library(
        name = name,
        hdrs = hdrs,
        includes = includes,
        linkstamp = source_name,
        visibility = ["//visibility:public"],
    )
