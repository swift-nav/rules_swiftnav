load("//tools:get_cc_files.bzl", "get_cc_files")

def _run_check_attributes(ctx, infile):
    output = ctx.actions.declare_file(infile.path + ".check-attributes.txt")

    ctx.actions.run_shell(
        inputs = [infile],
        outputs = [output],
        command = """
            result=0

            matches=$(grep -Hn __attribute__ "{infile}")

            touch {output}

            if [ -n "$matches" ];
            then
                while read -r line;
                do
                    echo "error: Do not use __attribute__, prefer one of the macros from swiftnav/macros.h" | tee {output}
                    echo "$line" | tee {output}
                    result=1
                done <<< $matches
            fi

            exit $result
        """.format(infile = infile.path, output = output.path),
    )
    return output

def _check_attributes_impl(target, ctx):
    # if not a C/C++ target, we are not interested
    if not CcInfo in target:
        return []

    outputs = []

    for file in get_cc_files(ctx):
        if file in ctx.files._excluded:
            continue
        outputs.append(_run_check_attributes(ctx, file))

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
