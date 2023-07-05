def _choose_clang_tidy(ctx):
    out = ctx.actions.declare_file("clang_tidy_bin.sh")

    ctx.actions.run_shell(
        outputs = [out],
        command = """
        if PATH=$PATH command -v clang-tidy-14 &> /dev/null
        then
            echo clang-tidy-14 \\"\\$@\\" > {0}
        elif PATH=$PATH command -v clang-tidy &> /dev/null
        then
            echo clang-tidy \\"\\$@\\" > {0}
        else
            err_msg='clang-tidy-14 / clang-tidy: command not found'
            echo $err_msg
            echo "echo "$err_msg">&2" >> {0}
            echo "exit 1" >> {0}
        fi
        """.format(out.path),
    )

    return [DefaultInfo(files = depset([out]))]

choose_clang_tidy = rule(
    implementation = _choose_clang_tidy,
)
