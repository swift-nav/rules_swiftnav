# Copyright (c) 2022 Synopsys, Inc. All rights reserved worldwide.
#
# This file defines a build setting value that can be used by users
# to specify additional action mnemonics that the integration should
# treat as link actions
EnableLinkInfo = provider(fields=["link_enabled"])


def _enable_link_impl(ctx):
    return EnableLinkInfo(link_enabled=ctx.build_setting_value)


enable_link = rule(
    implementation=_enable_link_impl, build_setting=config.bool(flag=True)
)
