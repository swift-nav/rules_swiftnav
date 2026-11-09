# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Module extension that fetches content-addressed S3 objects listed in a checked-in lockfile.

Each object is stored at `s3://<bucket>/<prefix>/<sha256>` and downloaded with
rules_s3's `s3_file`, so fetches go through Bazel's downloader, credential
helpers and repository cache.
"""

load("@rules_s3//s3:repo_rules.bzl", "s3_file")

def _s3_data_hub_impl(rctx):
    build = 'load("%s", "s3_data_runfile")\n\n' % Label(":s3_data.bzl")
    for path, src in sorted(rctx.attr.files.items()):
        build += 's3_data_runfile(name = "%s", src = "%s", path = "%s", visibility = ["//visibility:public"])\n' % (path, src, path)
    rctx.file("BUILD.bazel", build)
    return rctx.repo_metadata(reproducible = True)

_s3_data_hub = repository_rule(
    implementation = _s3_data_hub_impl,
    attrs = {
        "files": attr.string_dict(doc = "Workspace path -> label of the downloaded file."),
    },
)

_HEX = "0123456789abcdef"

def _check_entry(lockfile, path, sha256):
    if type(path) != "string" or not path or path.startswith("/") or ".." in path.split("/") or '"' in path:
        fail("s3_data: %s: invalid path %r" % (lockfile, path))
    if type(sha256) != "string" or len(sha256) != 64 or [c for c in sha256.elems() if c not in _HEX]:
        fail("s3_data: %s: invalid sha256 %r for %s" % (lockfile, sha256, path))

def _s3_data_impl(mctx):
    hubs = {}
    objects = {}
    for module in mctx.modules:
        for tag in module.tags.from_lockfile:
            if tag.name in hubs:
                fail("s3_data: duplicate hub name %s" % tag.name)
            lock = json.decode(mctx.read(tag.lockfile))
            if type(lock) != "dict":
                fail("s3_data: %s must be a JSON object of path -> sha256" % tag.lockfile)
            files = {}
            for path, sha256 in lock.items():
                _check_entry(tag.lockfile, path, sha256)
                url = "s3://%s/%s%s" % (tag.bucket, tag.prefix + "/" if tag.prefix else "", sha256)
                repo = "s3_data_" + sha256
                if repo not in objects:
                    objects[repo] = struct(url = url, sha256 = sha256, basename = path.split("/")[-1], endpoint = tag.endpoint)
                elif objects[repo].url != url or objects[repo].endpoint != tag.endpoint:
                    fail("s3_data: object %s is listed with two locations: %s and %s" % (sha256, objects[repo].url, url))
                files[path] = "@%s//file" % repo
            hubs[tag.name] = files

    for repo, obj in objects.items():
        kwargs = {"endpoint": obj.endpoint} if obj.endpoint else {}
        s3_file(
            name = repo,
            url = obj.url,
            sha256 = obj.sha256,
            downloaded_file_path = obj.basename,
            **kwargs
        )

    for name, files in hubs.items():
        _s3_data_hub(name = name, files = files)

    return mctx.extension_metadata(reproducible = True)

s3_data = module_extension(
    implementation = _s3_data_impl,
    tag_classes = {
        "from_lockfile": tag_class(
            doc = "Declares a hub repo `name` with one target per lockfile entry, named by its workspace path.",
            attrs = {
                "bucket": attr.string(mandatory = True, doc = "S3 bucket holding the objects."),
                "endpoint": attr.string(doc = "S3 endpoint, e.g. `s3.us-west-2.amazonaws.com`. Defaults to rules_s3's global endpoint."),
                "lockfile": attr.label(mandatory = True, doc = "JSON lockfile of workspace path -> sha256, see s3_data_lockfile."),
                "name": attr.string(mandatory = True, doc = "Name of the hub repo."),
                "prefix": attr.string(default = "sha256", doc = "Key prefix; objects live at `<prefix>/<sha256>`."),
            },
        ),
    },
)
