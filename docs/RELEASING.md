# Releasing

Cutting a release is two steps for a maintainer; the tag and GitHub release are
created automatically.

## 1. Open the release PR

```bash
bazel run //tools:release -- minor   # or: major / patch
```

This bumps `version` in `MODULE.bazel`, refreshes the example lockfile, extends
the copyright headers across the repo to the current year (e.g. `2022-2025` ->
`2022-2026`), and opens a PR titled `Bump version to X.Y.Z`. Use `--dry-run` to
preview the next version and how many headers would change without making any
changes.

Run it through `bazelisk` (the repo's `bazel` wrapper) so the example lockfile is
regenerated with the Bazel version pinned in `.bazeliskrc` — the same version CI
uses to validate it. The tool refuses to run if the active Bazel version differs
from that pin, since a mismatch would desync the lockfile digest from CI.

Review and merge the PR as normal.

## 2. (automatic) Tag + GitHub release

On merge to `main`, `.github/workflows/release.yaml` detects the `MODULE.bazel`
version change and creates the `vX.Y.Z` tag plus a GitHub release. Nothing to do.

## 3. Publish to the Bazel registry

The module is consumed via a separate Bazel registry. After the tag exists, run
the registry's sync tool from a checkout of that repository to stage and open the
registry PR — see that repository's README for the exact command. This step is
manual by design: it lives in a separate repository and is not driven from here.
