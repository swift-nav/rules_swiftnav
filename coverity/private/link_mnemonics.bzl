# Copyright (c) 2022 Synopsys, Inc. All rights reserved worldwide.
#
# This file defines a build setting value that can be used by users
# to specify additional action mnemonics that the integration should
# treat as link actions
LinkMnemonicInfo = provider(fields=["mnemonics"])


def _link_mnemonics_impl(ctx):
    return LinkMnemonicInfo(mnemonics=ctx.build_setting_value)


link_mnemonics = rule(
    implementation=_link_mnemonics_impl, build_setting=config.string_list(flag=True)
)
