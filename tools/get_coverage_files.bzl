load("//cc:defs.bzl", "BINARY", "LIBRARY")

FilesInfo = provider(
    fields = {
        "files": "files of the target",
    },
)

def _get_cov_files_aspect_impl(target, ctx):
    files = []

    if not CcInfo in target:
        return [FilesInfo(files = [])]

    tags = getattr(ctx.rule.attr, "tags", [])
    if not LIBRARY in tags and not BINARY in tags:
        return [FilesInfo(files = [])]

    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            for file in src.files.to_list():
                if file.is_source and not file.path.startswith("bazel-out/"):
                    files.append(file)

    if hasattr(ctx.rule.attr, "hdrs"):
        for hdr in ctx.rule.attr.hdrs:
            for file in hdr.files.to_list():
                if not file.path.startswith("bazel-out/"):
                    files.append(file)

    return [FilesInfo(files = files)]

_get_cov_files_aspect = aspect(
    implementation = _get_cov_files_aspect_impl,
    attr_aspects = ["deps"],
    attrs = {},
)

def _get_cov_files_rules_impl(ctx):
    out = ctx.actions.declare_file("target_files.sh")

    all_files = ""

    for file in ctx.attr.deps[0][FilesInfo].files:
        all_files += file.path
        all_files += " "

    ctx.actions.run_shell(
        outputs = [out],
        command = """
        touch {out_file}
        for file in {all_files}; do
            echo "echo '$file'" >> {out_file}
        done
        """.format(out_file = out.path, all_files = all_files),
    )
    return [
        DefaultInfo(
            executable = out,
            files = depset([out]),
        ),
    ]

get_cov_files_rules = rule(
    implementation = _get_cov_files_rules_impl,
    attrs = {
        "deps": attr.label_list(aspects = [_get_cov_files_aspect]),
    },
    executable = True,
)
