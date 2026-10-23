# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Module extension that fetches LFS objects listed in a checked-in lockfile.

The lockfile is the only input, so the generated repos are the same whether or
not the checkout has the LFS files pulled.
"""

load(":lfs.bzl", "lfs_file")

def _lfs_hub_impl(rctx):
    build = 'load("%s", "lfs_runfile")\n\n' % Label(":lfs.bzl")
    for path, src in sorted(rctx.attr.files.items()):
        build += 'lfs_runfile(name = "%s", src = "%s", path = "%s", visibility = ["//visibility:public"])\n' % (path, src, path)
    rctx.file("BUILD.bazel", build)
    return rctx.repo_metadata(reproducible = True)

_lfs_hub = repository_rule(
    implementation = _lfs_hub_impl,
    attrs = {
        "files": attr.string_dict(doc = "Workspace path -> label of the downloaded file."),
    },
)

_HEX = "0123456789abcdef"

def _check_entry(lockfile, path, oid):
    if type(path) != "string" or not path or path.startswith("/") or ".." in path.split("/") or '"' in path:
        fail("lfs: %s: invalid path %r" % (lockfile, path))
    if type(oid) != "string" or len(oid) != 64 or [c for c in oid.elems() if c not in _HEX]:
        fail("lfs: %s: invalid sha256 oid %r for %s" % (lockfile, oid, path))

def _lfs_impl(mctx):
    hubs = {}
    basenames = {}
    for module in mctx.modules:
        for tag in module.tags.from_lockfile:
            if tag.name in hubs:
                fail("lfs: duplicate hub name %s" % tag.name)
            lock = json.decode(mctx.read(tag.lockfile))
            if type(lock) != "dict":
                fail("lfs: %s must be a JSON object of path -> oid" % tag.lockfile)
            files = {}
            for path, oid in lock.items():
                _check_entry(tag.lockfile, path, oid)
                repo = "lfs_" + oid
                if repo not in basenames:
                    basenames[repo] = path.split("/")[-1]
                    lfs_file(name = repo, oid = oid, basename = basenames[repo], lfs_url = tag.lfs_url)
                files[path] = "@%s//file:%s" % (repo, basenames[repo])
            hubs[tag.name] = files

    for name, files in hubs.items():
        _lfs_hub(name = name, files = files)

    return mctx.extension_metadata(reproducible = True)

lfs = module_extension(
    implementation = _lfs_impl,
    tag_classes = {
        "from_lockfile": tag_class(
            doc = "Declares a hub repo `name` with one target per lockfile entry, named by its workspace path.",
            attrs = {
                "lfs_url": attr.string(mandatory = True, doc = "LFS server URL; objects are fetched from <lfs_url>/object/<oid>."),
                "lockfile": attr.label(mandatory = True, doc = "JSON lockfile of workspace path -> sha256 oid, see lfs_lockfile."),
                "name": attr.string(mandatory = True, doc = "Name of the hub repo."),
            },
        ),
    },
)
