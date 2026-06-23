# Releasing

Cutting a release is two steps for a maintainer; the tag and GitHub release are
created automatically.

## 1. Open the release PR

```bash
bazel run //tools:release -- minor   # or: major / patch
```

This bumps `version` in `MODULE.bazel`, refreshes the example lockfile, and opens
a PR titled `Bump version to X.Y.Z`. Use `--dry-run` to preview the next version
without making changes.

Review and merge the PR as normal.

## 2. (automatic) Tag + GitHub release

On merge to `main`, `.github/workflows/release.yaml` detects the `MODULE.bazel`
version change and creates the `vX.Y.Z` tag plus a GitHub release. Nothing to do.

## 3. Publish to the Bazel registry

The module is consumed via a separate Bazel registry. After the tag exists, run
the registry's sync tool from a checkout of that repository to stage and open the
registry PR — see that repository's README for the exact command. This step is
manual by design: it lives in a separate repository and is not driven from here.
