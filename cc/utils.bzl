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
