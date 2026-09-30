# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Tests for the check_test_naming aspect, rule and naming convention."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//check_test_naming:check_test_naming.bzl", "TestNamingInfo", "check_test_naming")
load("//check_test_naming:naming.bzl", "test_naming_errors")

def _naming_errors_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, [], test_naming_errors("foo_test", ["foo_test.cc"]))
    asserts.equals(env, [], test_naming_errors("foo_test", ["pkg/foo_test.py", "pkg/helper.py"]))
    asserts.equals(env, [], test_naming_errors("foo_test", ["helper.h", "data.json"]))
    asserts.equals(env, [], test_naming_errors("foo_test", []))

    asserts.equals(
        env,
        ["target name 'foo' must end with '_test'"],
        test_naming_errors("foo", ["foo_test.cc"]),
    )
    asserts.equals(
        env,
        ["target name 'test_foo_test' must not start with 'test_'"],
        test_naming_errors("test_foo_test", ["foo_test.cc"]),
    )
    asserts.equals(
        env,
        ["source 'pkg/test_foo_test.rs' must not start with 'test_'"],
        test_naming_errors("foo_test", ["pkg/test_foo_test.rs"]),
    )
    asserts.equals(
        env,
        ["at least one source must end with '_test', got: main.go, helper.go"],
        test_naming_errors("foo_test", ["main.go", "helper.go", "helper.h"]),
    )

    return unittest.end(env)

naming_errors_test = unittest.make(_naming_errors_test_impl)

def _aspect_errors_test_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    asserts.equals(env, ctx.attr.expected, target[TestNamingInfo].errors.to_list())
    return analysistest.end(env)

aspect_errors_test = analysistest.make(
    _aspect_errors_test_impl,
    attrs = {"expected": attr.string_list()},
    extra_target_under_test_aspects = [check_test_naming],
)

def _test_naming_test_script_test_impl(ctx):
    env = analysistest.begin(ctx)
    writes = [a for a in analysistest.target_actions(env) if a.mnemonic == "FileWrite"]
    asserts.equals(env, 1, len(writes))
    content = writes[0].content
    for expected in ctx.attr.expected:
        asserts.true(env, expected in content, "'{}' not in script:\n{}".format(expected, content))
    return analysistest.end(env)

test_naming_test_script_test = analysistest.make(
    _test_naming_test_script_test_impl,
    attrs = {"expected": attr.string_list()},
)
