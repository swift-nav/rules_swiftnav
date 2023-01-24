load("//cc:defs.bzl", "BINARY", "LIBRARY", "TEST", "TEST_LIBRARY")
load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

FilesInfo = provider(
    fields = {
        "files": "files of the target",
    },
)

def _get_cov_files_impl(target, ctx):
    files = []

    if not CcInfo in target:
        return [FilesInfo(files = [])]

    tags = getattr(ctx.rule.attr, "tags", [])
    if not LIBRARY in tags and \
       not BINARY in tags and \
       not TEST_LIBRARY in tags and \
       not TEST in tags:
        return [FilesInfo(files = [])]

    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            for file in src.files.to_list():
                if file.is_source and not file.path.startswith(ctx.genfiles_dir.path):
                    files.append(file)

    if hasattr(ctx.rule.attr, "hdrs"):
        for hdr in ctx.rule.attr.hdrs:
            for file in hdr.files.to_list():
                if not file.path.startswith(ctx.genfiles_dir.path):
                    files.append(file)

    return [FilesInfo(files = files)]

_get_cov_files = aspect(
    implementation = _get_cov_files_impl,
    attr_aspects = ["deps"],
    attrs = {},
)

def _gen_sonar_cfg_impl(ctx):
    all_files_bash = ""
    all_files = []

    for target in ctx.attr.targets:
        for file in target[FilesInfo].files:
            if file not in all_files:
                all_files_bash += file.path
                all_files_bash += " "
                all_files.append(file.path)

    out = ctx.actions.declare_file("sonar-project.properties")
    ctx.actions.run_shell(
        outputs = [out],
        command = """
        echo 'sonar.sourceEncoding=UTF-8' >> {out_file}
        echo 'sonar.sources=\\' >> {out_file}
        first=1
        for file in {all_files}; do
            if [[ $first -eq 1 ]]
            then
                first=0
            else
                echo ',\\' >> {out_file}
            fi
            echo -n "  {root_dir}/$file" >> {out_file}
        done
        echo '' >> {out_file}
        """.format(
            out_file = out.path,
            all_files = all_files_bash,
            root_dir = ctx.attr.root_dir[BuildSettingInfo].value,
        ),
    )

    return [DefaultInfo(files = depset([out]))]

gen_sonar_cfg = rule(
    implementation = _gen_sonar_cfg_impl,
    attrs = {
        "targets": attr.label_list(aspects = [_get_cov_files]),
        "root_dir": attr.label(default = Label("//tools:root_dir")),
    },
)
