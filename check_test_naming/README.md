# check_test_naming

A Bazel [aspect](https://bazel.build/extending/aspects) and test rule that
enforce the test naming convention on test targets of any language, following
the [Bazel style guide](https://bazel.build/build/style-guide) and
[GoogleTest](https://google.github.io/googletest/primer.html): tests are named
with a `_test` suffix, not a `test_` prefix.

## The convention

For every target whose rule kind ends with `_test` (`cc_test`, `py_test`,
`rust_test`, `go_test`, `sh_test`, `swift_cc_test`'s underlying `cc_test`, ...):

- the target name ends with `_test`,
- the target name does not start with `test_`,
- no source file name starts with `test_`,
- at least one source file name ends with `_test`, if the target has any.

```python
# OK
cc_test(name = "fibonacci_test", srcs = ["fibonacci_test.cc"])
py_test(name = "release_test", srcs = ["release.py", "release_test.py"])

# Rejected
cc_test(name = "fibonacci", srcs = ["fibonacci_test.cc"])           # name lacks '_test'
py_test(name = "test_release", srcs = ["test_release.py"])          # 'test_' prefix
cc_test(name = "fibonacci_test", srcs = ["main.cc", "helper.cc"])   # no '*_test' source
```

Only source files in the test's own package with one of the extensions in
`SOURCE_EXTENSIONS` (`naming.bzl`) are checked: headers, data files, generated
files and files borrowed from other packages are ignored. Helpers such as
`main.cc` or `release.py` are fine next to a `*_test` file.

To exempt a target, tag it `no-test-naming-check`.

## Usage

### From the command line, over a whole repository

Run the aspect over the targets to check. It fails the build and prints every
violation:

```bash
bazel build \
  --aspects @rules_swiftnav//check_test_naming:check_test_naming.bzl%check_test_naming \
  --output_groups=report \
  --keep_going \
  //...
```

```
//tools/lint:test_lint: target name 'test_lint' must end with '_test'
//tools/lint:test_lint: target name 'test_lint' must not start with 'test_'
//tools/lint:test_lint: source 'tools/lint/test_lint.py' must not start with 'test_'
```

Or add a config to `.bazelrc`:

```
build:check-test-naming --aspects @rules_swiftnav//check_test_naming:check_test_naming.bzl%check_test_naming
build:check-test-naming --output_groups=report
```

```bash
bazel build --config=check-test-naming //...
```

### As a test

`test_naming_test` applies the aspect to its `targets` and fails when any of
them violates the convention, so `bazel test` catches violations without extra
flags. It follows `test_suite`s, including ones without `tests`, which cover
every non-manual test of their package.

An implicit `test_suite` in the same package would include the
`test_naming_test` itself, which is a dependency cycle, so exclude it by tag:

```python
load("@rules_swiftnav//check_test_naming:check_test_naming.bzl", "test_naming_test")

# Every test in this package but the naming test
test_suite(
    name = "tests",
    tags = ["-test_naming"],
)

test_naming_test(
    name = "naming_test",
    tags = ["test_naming"],
    targets = [":tests"],
)
```

A rule can't depend on a wildcard such as `//...`, so use the command line form
to check a whole repository at once.

## Limitations

- Only source files of languages using `snake_case` file names are checked.
  Java/Kotlin sources (`FooTest.java`) are ignored, but their `FooTest` target
  names are rejected: tag them `no-test-naming-check`.
