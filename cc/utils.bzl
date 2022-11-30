# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

def construct_local_include(path):
    """Helper to correctly set up local (non-public) include paths.

    When a bazel workspace is consumed externally, (i.e. via local_repository),
    its sources are placed under <execroot>/external/<workspace_root>/. This
    typically breaks local include paths defined using -I.

    This macro ensures that the include path is constructed correctly both when
    building a workpace standalone, and externally.

    Args:
        path: The include path relative to the package this macro is called from

            Use the special argument $(GENDIR) to construct an include path for
            any generated files the build depends on.

    """
    root = Label(native.repository_name() + "//:WORKSPACE").workspace_root or "."
    package = native.package_name()

    # Generated files are placed in $(GENDIR)/external/<workspace_root>
    if path == "$(GENDIR)":
        return "-I" + path + "/" + root + "/" + package + "/"
    else:
        return "-I" + root + "/" + package + "/" + path + "/"
