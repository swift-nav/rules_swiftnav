def _choose_clang_format(ctx):
    out = ctx.actions.declare_file("clang_format_bin.sh")

    ctx.actions.run_shell(
        outputs = [out],
        command = """
        if command -v clang-format-14 &> /dev/null
        then
            echo clang-format-14 \\"\\$@\\" > {0}
        elif command -v clang-format &> /dev/null
        then
            echo clang-format \\"\\$@\\" > {0}
        else
            echo "clang-format-14 / clang-format: command not found"
            exit 1
        fi
        """.format(out.path),
    )

    return [DefaultInfo(files = depset([out]))]

choose_clang_format = rule(
    implementation = _choose_clang_format,
)
