# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@bazel_skylib//lib:paths.bzl", "paths")

def construct_local_include(path):
    """Helper to correctly set up local (non-public) include paths.

    When a bazel workspace is consumed externally, (i.e. via local_repository),
    its sources are placed under <execroot>/external/<workspace_root>/. This
    typically breaks local include paths defined using -I.

    This macro ensures that the include path is constructed correctly both when
    building a workpace standalone, and externally.

    Args:
        path: The include path relative to the package this macro is called from

            Prefix the path with $(GENDIR) to construct an include path for
            generated files the build depends on.
    """
    repo_name = native.repository_name()[1:]
    package_name = native.package_name()

    # An include path into the generated tree is only emitted on request:
    # unconditionally adding one makes -Wmissing-include-dirs fire for every
    # package that has no generated files, since bazel never creates the dir.
    gendir = path.startswith("$(GENDIR)")
    if gendir:
        path = path[len("$(GENDIR)"):].lstrip("/")

    if repo_name:
        include_dir = paths.join("external", repo_name, package_name, path)
    else:
        include_dir = paths.join(package_name, path)

    if gendir:
        include_dir = paths.join("$(GENDIR)", include_dir)

    return ["-I{}".format(include_dir)]

def _test_name_error(kind, name):
    if not name.endswith("_test") or name.startswith("test_"):
        return "{} must be named with a '_test' suffix and no 'test_' prefix".format(kind)
    return None

def test_naming_error(name, srcs):
    """Checks that a test target and its sources follow the test naming convention.

    The target name and the stem of every C/C++ source file listed in srcs must
    end with '_test' and must not start with 'test_'.

    Args:
        name: The name of the test target.
        srcs: The srcs of the test target. Labels, non-C/C++ files and select()
            values are ignored since they can't be inspected by a macro.

    Returns:
        An error message describing the first violation, or None.
    """
    error = _test_name_error("Test target '{}'".format(name), name)
    if error:
        return error

    if type(srcs) != "list":
        return None

    for src in srcs:
        # Labels refer to other targets, not files owned by this test
        if type(src) != "string" or src.startswith(":") or src.startswith("//") or src.startswith("@"):
            continue
        stem, _, ext = paths.basename(src).rpartition(".")
        if ext not in ["c", "cc", "cpp", "cxx"]:
            continue
        error = _test_name_error("Test source '{}' of '{}'".format(src, name), stem)
        if error:
            return error

    return None
