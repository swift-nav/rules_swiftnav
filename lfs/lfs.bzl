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

def _lfs_runfile_impl(ctx):
    f = ctx.file.src

    # Tests open LFS files by their workspace path, so also place the file there in runfiles.
    return [DefaultInfo(
        files = depset([f]),
        runfiles = ctx.runfiles(files = [f], symlinks = {ctx.attr.path: f}),
    )]

lfs_runfile = rule(
    implementation = _lfs_runfile_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True),
        "path": attr.string(mandatory = True),
    },
)
