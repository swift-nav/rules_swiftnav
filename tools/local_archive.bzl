def _impl(repository_ctx):
    repository_ctx.extract(
        archive = repository_ctx.attr.src,
        stripPrefix = repository_ctx.attr.strip_prefix,
    )
    repository_ctx.file(
        "BUILD.bazel",
        repository_ctx.attr.build_file_content,
    )

local_archive = repository_rule(
    implementation = _impl,
    attrs = {
        "src": attr.label(mandatory = True, allow_single_file = True),
        "build_file_content": attr.string(mandatory = True),
        "sha256": attr.string(),
        "strip_prefix": attr.string(),
    },
)
