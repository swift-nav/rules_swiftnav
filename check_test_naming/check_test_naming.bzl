# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Enforces the test naming convention on test targets of any language."""

load(":naming.bzl", "test_naming_errors")

# Tag that exempts a test target from the naming check
NO_TEST_NAMING_CHECK = "no-test-naming-check"

# test_suite attributes that hold its tests
_SUITE_ATTRS = ["tests", "_implicit_tests"]

TestNamingInfo = provider(
    doc = "Test naming violations of a target and, for a test_suite, of its tests.",
    fields = {
        "errors": "depset of error messages, each prefixed with the offending target's label",
        "reports": "depset of report files whose actions fail when there are errors",
    },
)

def _is_checked_test(ctx):
    # Bazel requires every test rule's name to end with '_test'
    return ctx.rule.kind.endswith("_test") and NO_TEST_NAMING_CHECK not in ctx.rule.attr.tags

def _own_srcs(ctx):
    """Returns the source files in the test's srcs that live in its own package."""
    return [
        f.short_path
        for f in getattr(ctx.rule.files, "srcs", [])
        if f.is_source and
           f.owner.workspace_name == ctx.label.workspace_name and
           f.owner.package == ctx.label.package
    ]

def _display_label(label):
    # str(label) renders main repository labels as '@@//pkg:name'
    repo = "@" + label.workspace_name if label.workspace_name else ""
    return "{}//{}:{}".format(repo, label.package, label.name)

def _report(ctx, errors):
    errors_file = ctx.actions.declare_file(ctx.label.name + ".test_naming_errors.txt")
    ctx.actions.write(errors_file, "\n".join(errors) + "\n")

    report = ctx.actions.declare_file(ctx.label.name + ".test_naming.txt")
    ctx.actions.run_shell(
        inputs = [errors_file],
        outputs = [report],
        command = "cat {} >&2; exit 1".format(errors_file.path),
        mnemonic = "CheckTestNaming",
        progress_message = "Checking test naming of %{label}",
    )
    return report

def _check_test_naming_impl(_target, ctx):
    errors = []
    if _is_checked_test(ctx):
        errors = [
            "{}: {}".format(_display_label(ctx.label), error)
            for error in test_naming_errors(ctx.label.name, _own_srcs(ctx))
        ]

    # A test_suite aggregates the violations of its tests, which are held in
    # '_implicit_tests' when 'tests' is empty
    suite_tests = [
        t[TestNamingInfo]
        for attr in _SUITE_ATTRS
        for t in getattr(ctx.rule.attr, attr, [])
        if TestNamingInfo in t
    ]

    reports = depset(
        [_report(ctx, errors)] if errors else [],
        transitive = [info.reports for info in suite_tests],
    )

    return [
        TestNamingInfo(
            errors = depset(errors, transitive = [info.errors for info in suite_tests]),
            reports = reports,
        ),
        OutputGroupInfo(report = reports),
    ]

check_test_naming = aspect(
    implementation = _check_test_naming_impl,
    attr_aspects = _SUITE_ATTRS,
    doc = """Checks that test targets follow the test naming convention.

    Applies to every target whose rule kind ends with '_test', regardless of
    language, and follows the 'tests' of test_suites. Violations are reported by
    building the 'report' output group, which fails when there are any.
    """,
)

def _test_naming_test_impl(ctx):
    errors = depset(transitive = [t[TestNamingInfo].errors for t in ctx.attr.targets]).to_list()

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    if errors:
        content = "#!/usr/bin/env bash\ncat >&2 <<'EOF'\nTest naming violations:\n{}\nEOF\nexit 1\n".format("\n".join(errors))
    else:
        content = "#!/usr/bin/env bash\nexit 0\n"
    ctx.actions.write(script, content, is_executable = True)

    return [DefaultInfo(executable = script)]

test_naming_test = rule(
    implementation = _test_naming_test_impl,
    test = True,
    attrs = {
        "targets": attr.label_list(
            aspects = [check_test_naming],
            doc = "Test targets or test_suites to check.",
        ),
    },
    doc = "Test that fails when any of `targets` violates the test naming convention.",
)
