# rules_swiftnav

Swift Navigation's bazel rules.

The contents of this repository are subject to change frequently.

## Documentation

- [check_attributes](check_attributes/README.md) — aspect that bans raw
  `__attribute__` in C/C++ code in favour of guard macros in
  `libswiftnav/macros.h`.
- [check_test_naming](check_test_naming/README.md) — aspect and test rule that
  enforce the `_test` suffix (and ban the `test_` prefix) on test targets and
  their source files, for any language.
- [Releasing](docs/RELEASING.md) — how to cut a release.

# LICENSE

Copyright © 2026 Swift Navigation

Distributed under MIT.
