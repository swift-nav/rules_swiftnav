def qac_compile_commands(name, tool, **kwargs):
    """Replaces -isystem with -I in a compile_commands.json file.

    This is necessary to get Helix QAC to work correctly.

    Args:
        name: A unique label for this rule.
        tool: A label refrencing a @hedron_compile_commands:refresh_compile_commands target.

    """
    arg = "$(location {})".format(tool)
    native.sh_binary(
        name = name,
        # FIXME: Assumes //bazel is a valid label in the consuming workspace.
        srcs = ["//bazel:qac_compile_commands.sh"],
        args = [arg],
        data = [tool],
        **kwargs
    )
