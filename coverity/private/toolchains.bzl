# Copyright (c) 2023 Synopsys, Inc. All rights reserved worldwide.
def _coverity_toolchain_impl(ctx):
    return [platform_common.ToolchainInfo(helper=ctx.attr.helper)]


coverity_toolchain = rule(
    implementation=_coverity_toolchain_impl,
    attrs={"helper": attr.label(allow_single_file=True, executable=True, cfg="exec")},
)


def _empty_toolchain_impl(ctx):
    return [platform_common.ToolchainInfo()]


empty_toolchain = rule(implementation=_empty_toolchain_impl)
