# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

def qac_compile_commands(name, tool, **kwargs):
    """Replaces -isystem with -I in a compile_commands.json file.

    This is necessary to get Helix QAC to work correctly.

    Args:
        name: A unique label for this rule.
        tool: A label refrencing a @hedron_compile_commands:refresh_compile_commands target.

    """
    arg = "$(location {})".format(tool)
    native.sh_binary(
        name = name,
        srcs = [Label("//tools:qac_compile_commands.sh")],
        args = [arg],
        data = [tool],
        **kwargs
    )
