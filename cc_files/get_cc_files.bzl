load("//cc:defs.bzl", "BINARY", "LIBRARY", "TEST_LIBRARY", "TEST_SRCS")

FilesInfo = provider(
    fields = {
        "files": "files of the target",
        "test_files": "test files of the target",
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
        return [FilesInfo(files = [], test_files = [])]

    tags = getattr(ctx.rule.attr, "tags", [])

    if LIBRARY in tags or BINARY in tags:
        return [FilesInfo(files = get_cc_files(ctx), test_files = [])]

    if TEST_LIBRARY in tags:
        return [FilesInfo(files = [], test_files = get_cc_files(ctx))]

    return [FilesInfo(files = [], test_files = [])]

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

def _get_cc_test_srcs_impl(target, ctx):
    tags = getattr(ctx.rule.attr, "tags", [])
    if not TEST_SRCS in tags:
        return [OutputGroupInfo(report = [])]

    output = ctx.actions.declare_file(ctx.rule.attr.name + "_test_srcs.txt")
    srcs = " ".join([f.path for f in get_cc_srcs(ctx) if f.extension != "h" and f.extension != "hpp"])

    ctx.actions.run_shell(
        inputs = [],
        outputs = [output],
        command = """
            touch {output}
            for s in {srcs}
            do
                echo $s >> {output}
            done
        """.format(output = output.path, srcs = srcs),
    )

    return [OutputGroupInfo(report = depset(direct = [output]))]

get_cc_test_srcs = aspect(
    implementation = _get_cc_test_srcs_impl,
)
