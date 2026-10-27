# lfs

Fetches Git LFS objects through Bazel instead of `git lfs pull`. A checked-in
lockfile maps workspace paths to LFS oids and is the only input of the `lfs`
module extension, so CI checkouts with LFS pointers and developer checkouts
with pulled files get the same repos and the same test action keys.

```starlark
# MODULE.bazel
lfs = use_extension("@rules_swiftnav//lfs:extensions.bzl", "lfs")
lfs.from_lockfile(
    name = "lfs_test_data",
    lfs_url = "https://lfs.example.com",
    lockfile = "//:lfs.lock.json",
)
use_repo(lfs, "lfs_test_data")
```

```starlark
# BUILD.bazel
load("@rules_swiftnav//lfs:defs.bzl", "lfs_lockfile")

exports_files(["lfs.lock.json"])

lfs_lockfile(
    name = "lfs_lock",
    srcs = ["//test_data:all_files"],
    lockfile = "lfs.lock.json",
)
```

`bazel run //:lfs_lock.update` regenerates the lockfile from the files that
`.gitattributes` tracks with LFS, and `//:lfs_lock.update_test` fails when it is
stale. Tests depend on `@lfs_test_data//:test_data/foo/bar.pb`, which places the
object in runfiles at `test_data/foo/bar.pb`.
