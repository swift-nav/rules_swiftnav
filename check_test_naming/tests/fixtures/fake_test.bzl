# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""A language-agnostic test rule used as a fixture for check_test_naming."""

def _fake_test_impl(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(script, "#!/usr/bin/env bash\nexit 0\n", is_executable = True)
    return [DefaultInfo(executable = script)]

fake_test = rule(
    implementation = _fake_test_impl,
    test = True,
    attrs = {"srcs": attr.label_list(allow_files = True)},
)
