# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Unit tests for utils.bzl."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load(":utils.bzl", "test_naming_error")

def _valid_names_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, None, test_naming_error("foo_test", ["foo_test.cc"]))
    asserts.equals(env, None, test_naming_error("foo_test", ["test/foo_test.c"]))
    asserts.equals(env, None, test_naming_error("foo_test", ["a_test.cpp", "b_test.cxx"]))
    asserts.equals(env, None, test_naming_error("foo_test", []))
    return unittest.end(env)

valid_names_test = unittest.make(_valid_names_test_impl)

def _invalid_target_name_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        "Test target 'foo' must be named with a '_test' suffix and no 'test_' prefix",
        test_naming_error("foo", ["foo_test.cc"]),
    )
    asserts.equals(
        env,
        "Test target 'test_foo' must be named with a '_test' suffix and no 'test_' prefix",
        test_naming_error("test_foo", ["foo_test.cc"]),
    )
    asserts.equals(
        env,
        "Test target 'test_foo_test' must be named with a '_test' suffix and no 'test_' prefix",
        test_naming_error("test_foo_test", ["foo_test.cc"]),
    )
    return unittest.end(env)

invalid_target_name_test = unittest.make(_invalid_target_name_test_impl)

def _invalid_source_name_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        "Test source 'foo.cc' of 'foo_test' must be named with a '_test' suffix and no 'test_' prefix",
        test_naming_error("foo_test", ["foo.cc"]),
    )
    asserts.equals(
        env,
        "Test source 'test/test_foo.c' of 'foo_test' must be named with a '_test' suffix and no 'test_' prefix",
        test_naming_error("foo_test", ["test/test_foo.c"]),
    )
    asserts.equals(
        env,
        "Test source 'test_foo_test.cc' of 'foo_test' must be named with a '_test' suffix and no 'test_' prefix",
        test_naming_error("foo_test", ["bar_test.cc", "test_foo_test.cc"]),
    )
    return unittest.end(env)

invalid_source_name_test = unittest.make(_invalid_source_name_test_impl)

def _ignored_srcs_test_impl(ctx):
    env = unittest.begin(ctx)

    # Headers, non-C/C++ files and labels to other targets are not checked
    asserts.equals(env, None, test_naming_error("foo_test", ["helper.h", "helper.hpp", "data.json"]))
    asserts.equals(env, None, test_naming_error("foo_test", [":helper", "//pkg:helper.cc", "@repo//pkg:helper.cc"]))
    asserts.equals(env, None, test_naming_error("foo_test", [Label("//pkg:helper.cc")]))

    # The contents of a select() can't be inspected
    asserts.equals(env, None, test_naming_error("foo_test", select({"//conditions:default": ["helper.cc"]})))
    return unittest.end(env)

ignored_srcs_test = unittest.make(_ignored_srcs_test_impl)

def utils_test_suite(name):
    unittest.suite(
        name,
        valid_names_test,
        invalid_target_name_test,
        invalid_source_name_test,
        ignored_srcs_test,
    )
