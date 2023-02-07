load("//cc:defs.bzl", "BINARY", "LIBRARY", "TEST_LIBRARY")

FilesInfo = provider(
    fields = {
        "files": "files of the target",
    },
)

def _get_hdrs(ctx):
    files = []

    if hasattr(ctx.rule.attr, "hdrs"):
        for hdr in ctx.rule.attr.hdrs:
            for file in hdr.files.to_list():
                if not file.path.startswith(ctx.genfiles_dir.path):
                    files.append(file)
    return files

def _get_srcs(ctx):
    files = []

    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            for file in src.files.to_list():
                if file.is_source and not file.path.startswith(ctx.genfiles_dir.path):
                    files.append(file)
    return files

def _get_cc_target_files_impl(target, ctx):
    files = []

    if not CcInfo in target:
        return [FilesInfo(files = [])]

    tags = getattr(ctx.rule.attr, "tags", [])
    if not LIBRARY in tags and not TEST_LIBRARY in tags and not BINARY in tags:
        return [FilesInfo(files = [])]

    files.extend(_get_srcs(ctx))

    files.extend(_get_hdrs(ctx))

    return [FilesInfo(files = files)]

get_cc_target_files = aspect(
    implementation = _get_cc_target_files_impl,
)

def _get_cc_target_hdrs_impl(target, ctx):
    if not CcInfo in target:
        return [FilesInfo(files = [])]

    return [FilesInfo(files = _get_hdrs(ctx))]

get_cc_target_hdrs = aspect(
    implementation = _get_cc_target_hdrs_impl,
)
