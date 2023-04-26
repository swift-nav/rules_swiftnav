load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _string_list_file(ctx):
    out = ctx.actions.declare_file(ctx.attr.name + ".txt")

    ctx.actions.run_shell(
        outputs = [out],
        command = """
        touch {out}
        for s in {string_list}
        do
            echo $s >> {out}
        done
        """.format(
            out = out.path,
            string_list = " ".join(ctx.attr.string_list[BuildSettingInfo].value),
        ),
    )

    return [DefaultInfo(files = depset([out]))]

string_list_file = rule(
    implementation = _string_list_file,
    attrs = {
        "string_list": attr.label(mandatory = True),
    },
)
