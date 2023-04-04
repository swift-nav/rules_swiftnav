load("//cc:defs.bzl", "BINARY", "LIBRARY", "TEST_LIBRARY")

FilesInfo = provider(
    fields = {
        "files": "files of the target",
    },
)

def get_cc_hdrs(ctx):
    hdrs = []

    if hasattr(ctx.rule.attr, "hdrs"):
        for hdr in ctx.rule.attr.hdrs:
            hdrs += [hdr for hdr in hdr.files.to_list() if hdr.is_source]

    return hdrs

def get_cc_srcs(ctx):
    srcs = []

    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            srcs += [src for src in src.files.to_list() if src.is_source]

    return srcs

def get_cc_files(ctx):
    files = []

    files.extend(get_cc_srcs(ctx))
    files.extend(get_cc_hdrs(ctx))

    return files

def _get_cc_target_files_impl(target, ctx):
    if not CcInfo in target:
        return [FilesInfo(files = [])]

    tags = getattr(ctx.rule.attr, "tags", [])
    if not LIBRARY in tags and not TEST_LIBRARY in tags and not BINARY in tags:
        return [FilesInfo(files = [])]

    return [FilesInfo(files = get_cc_files(ctx))]

get_cc_target_files = aspect(
    implementation = _get_cc_target_files_impl,
)

def _get_cc_target_hdrs_impl(target, ctx):
    if not CcInfo in target:
        return [FilesInfo(files = [])]

    return [FilesInfo(files = get_cc_hdrs(ctx))]

get_cc_target_hdrs = aspect(
    implementation = _get_cc_target_hdrs_impl,
)
