load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load("//tools:get_files.bzl", "FilesInfo", "get_target_files")

def _gen_sonar_cfg_impl(ctx):
    all_files_bash = ""
    all_files = []

    for target in ctx.attr.targets:
        for file in target[FilesInfo].files + ctx.files.test_srcs:
            if file.path not in all_files:
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
        "targets": attr.label_list(aspects = [get_target_files]),
        "test_srcs": attr.label_list(),
        "root_dir": attr.label(default = Label("//tools:root_dir")),
    },
)
