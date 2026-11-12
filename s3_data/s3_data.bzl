# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Build rule backing the `s3_data` module extension's hub repo."""

def _s3_data_runfile_impl(ctx):
    f = ctx.file.src

    # Tests open data files by their workspace path, so also place the file there in runfiles.
    return [DefaultInfo(
        files = depset([f]),
        runfiles = ctx.runfiles(files = [f], symlinks = {ctx.attr.path: f}),
    )]

s3_data_runfile = rule(
    implementation = _s3_data_runfile_impl,
    doc = "Exposes a downloaded object, also at its workspace path in runfiles.",
    attrs = {
        "path": attr.string(mandatory = True, doc = "Workspace-relative path the file is linked at in runfiles."),
        "src": attr.label(allow_single_file = True, mandatory = True, doc = "The downloaded file."),
    },
)
