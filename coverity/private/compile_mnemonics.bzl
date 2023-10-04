# Copyright (c) 2021 Synopsys, Inc. All rights reserved worldwide.
#
# This file defines a build setting value that can be used by users
# to specify additional action mnemonics that the integration should
# treat as compilation actions
CompileMnemonicInfo = provider(fields=["mnemonics"])


def _compile_mnemonics_impl(ctx):
    return CompileMnemonicInfo(mnemonics=ctx.build_setting_value)


compile_mnemonics = rule(
    implementation=_compile_mnemonics_impl, build_setting=config.string_list(flag=True)
)
