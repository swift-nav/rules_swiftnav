def _lfs_file_impl(rctx):
    rctx.download(
        url = "%s/object/%s" % (rctx.attr.lfs_url, rctx.attr.oid),
        output = "file/" + rctx.attr.basename,
        sha256 = rctx.attr.oid,
    )
    rctx.file("file/BUILD.bazel", 'exports_files(["' + rctx.attr.basename + '"])')
    return rctx.repo_metadata(reproducible = True)

lfs_file = repository_rule(
    implementation = _lfs_file_impl,
    attrs = {
        "oid": attr.string(mandatory = True),
        "basename": attr.string(mandatory = True),
        "lfs_url": attr.string(mandatory = True),
    },
)
