# s3_data

Fetches data files (e.g. test data) from S3 through Bazel. A checked-in
lockfile maps workspace paths to sha256 digests. Each object is stored at
`s3://<bucket>/<prefix>/<sha256>` and downloaded with
[rules_s3](https://github.com/tweag/rules_s3)'s `s3_file`, so downloads are
verified, deduplicated by content and cached in the repository cache. The
files themselves are not in git.

The lockfile has the same format as the one from [lfs](../lfs/README.md), so a
repo moving off Git LFS can keep its lockfile after copying the objects to S3.

```starlark
# MODULE.bazel
s3_data = use_extension("@rules_swiftnav//s3_data:extensions.bzl", "s3_data")
s3_data.from_lockfile(
    name = "test_data",
    bucket = "my-test-data",
    endpoint = "s3.us-west-2.amazonaws.com",
    lockfile = "//:test_data.lock.json",
)
use_repo(s3_data, "test_data")
```

```starlark
# BUILD.bazel
load("@rules_swiftnav//s3_data:defs.bzl", "s3_data_lockfile")

exports_files(["test_data.lock.json"])

s3_data_lockfile(
    name = "test_data",
    bucket = "my-test-data",
    lockfile = "test_data.lock.json",
)
```

Tests depend on `@test_data//:data/foo/bar.pb`, which places the object in
runfiles at `data/foo/bar.pb`, so test code opens files by their workspace path.

## Adding and fetching data

```sh
# Upload new or changed files and record them in the lockfile, then commit it.
bazel run //:test_data.upload -- data/foo/new.pb

# Copy lockfile entries into the workspace for use outside Bazel.
bazel run //:test_data.fetch -- data/foo
```

Both tools shell out to the `aws` CLI and use the caller's AWS credentials.
Objects that already exist are not uploaded again. Keep the fetched paths in
`.gitignore`.

## Authentication

The module extension passes no credentials itself. Bazel's downloader signs S3
requests through a credential helper, e.g.
[tweag-credential-helper](https://github.com/tweag/credential-helper):

```
# .bazelrc
common --credential_helper=s3.us-west-2.amazonaws.com=%workspace%/tools/credential-helper
```
