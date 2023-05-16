load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load("//cc_files:get_cc_files.bzl", "FilesInfo", "get_cc_target_files")

def _gen_sonar_cfg_impl(ctx):
    files_bash = ""
    files = []

    for target in ctx.attr.targets:
        for file in target[FilesInfo].files:
            if file.path not in files:
                files_bash += file.path
                files_bash += " "
                files.append(file.path)

    test_files_bash = ""
    test_files = []

    for target in ctx.attr.targets:
        for file in target[FilesInfo].test_files:
            if file.path not in test_files:
                test_files_bash += file.path
                test_files_bash += " "
                test_files.append(file.path)

    for file in ctx.files.test_srcs:
        if file.path not in test_files:
            test_files_bash += file.path
            test_files_bash += " "
            test_files.append(file.path)

    out = ctx.actions.declare_file("sonar-project.properties")
    ctx.actions.run_shell(
        outputs = [out],
        command = """
        add_files () {{
            files=$1
            first=1
            for file in $files; do
                if [[ $first -eq 1 ]]
                then
                    first=0
                else
                    echo ',\\' >> {out_file}
                fi
                echo -n "  {root_dir}/$file" >> {out_file}
            done
            echo '' >> {out_file}
        }}

        echo 'sonar.sourceEncoding=UTF-8' >> {out_file}

        echo 'sonar.inclusions=\\' >> {out_file}
        add_files "{inclusions}"

        echo 'sonar.coverage.exclusions=\\' >> {out_file}
        add_files "{exclusions}"

        echo 'sonar.cpd.exclusions=\\' >> {out_file}
        add_files "{exclusions}"
        """.format(
            out_file = out.path,
            inclusions = files_bash + " " + test_files_bash,
            exclusions = test_files_bash,
            root_dir = ctx.attr.root_dir[BuildSettingInfo].value,
        ),
    )

    return [DefaultInfo(files = depset([out]))]

gen_sonar_cfg = rule(
    implementation = _gen_sonar_cfg_impl,
    attrs = {
        "targets": attr.label_list(aspects = [get_cc_target_files]),
        "test_srcs": attr.label_list(),
        "root_dir": attr.label(default = Label("//tools:root_dir")),
    },
)
