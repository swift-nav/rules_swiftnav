# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Repository and build rules backing the `lfs` module extension's hub repo."""

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
    doc = "Downloads one LFS object by oid and exports it as `//file:<basename>`.",
    attrs = {
        "oid": attr.string(mandatory = True, doc = "sha256 of the object, also used to verify the download."),
        "basename": attr.string(mandatory = True, doc = "File name of the exported file."),
        "lfs_url": attr.string(mandatory = True, doc = "LFS server URL; the object is fetched from <lfs_url>/object/<oid>."),
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
    doc = "Exposes a downloaded LFS file, also at its workspace path in runfiles.",
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True, doc = "The downloaded file."),
        "path": attr.string(mandatory = True, doc = "Workspace-relative path the file is linked at in runfiles."),
    },
)
