def _run_check_attributes(ctx, infile, discriminator):
    outfile = ctx.actions.declare_file(
        "bazel_check_attribute_" + infile.path + "." + discriminator + ".txt",
    )

    ctx.actions.run_shell(
        inputs = [infile],
        outputs = [outfile],
        command = """
            result=0

            matches=$(grep -Hn __attribute__ "{infile}")

            touch {outfile}

            if [ -n "$matches" ];
            then
                while read -r line;
                do
                    echo "error: Do not use __attribute__, prefer one of the macros from swiftnav/macros.h" | tee {outfile}
                    echo "$line" | tee {outfile}
                    result=1
                done <<< $matches
            fi

            exit $result
        """.format(infile = infile.path, outfile = outfile.path),
    )
    return outfile

def _rule_files(ctx):
    files = []
    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            files += [src for src in src.files.to_list() if src.is_source]

    if hasattr(ctx.rule.attr, "hdrs"):
        for hdr in ctx.rule.attr.hdrs:
            files += [hdr for hdr in hdr.files.to_list() if hdr.is_source]
    return files

def _check_attributes_impl(target, ctx):
    # if not a C/C++ target, we are not interested
    if not CcInfo in target:
        return []

    outputs = []

    for file in _rule_files(ctx):
        if file in ctx.files._excluded:
            continue
        outputs.append(_run_check_attributes(ctx, file, target.label.name))

    return [
        OutputGroupInfo(report = depset(direct = outputs)),
    ]

check_attributes = aspect(
    implementation = _check_attributes_impl,
    fragments = ["cpp"],
    attrs = {
        "_excluded": attr.label(default = Label("//check_attributes:excluded")),
    },
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
)
