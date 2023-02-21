load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load(
    "//cc/toolchain/internal:common.bzl",
    _canonical_dir_path = "canonical_dir_path",
    _host_or_arch_dict_value = "host_os_arch_dict_value",
    _pkg_path_from_label = "pkg_path_from_label",
    _toolchain_tools = "toolchain_tools",
)

def _llvm_repo_impl(rctx):
    # only support linux
    print("Downloading llvm")
    if rctx.os.name != "linux":
        return

    rctx.file(
        "BUILD.bazel",
        content = rctx.read(Label("//cc/toolchain:BUILD.llvm_repo")),
        executable = False,
    )

    _url = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz"
    strip_prefix = "clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04"
    res = rctx.download_and_extract(
        url = _url,
        stripPrefix = strip_prefix,
    )

    return None

def _toolchain_impl(rctx):
    print("toolchain_impl is running")
    if rctx.os.name != "linux":
        return

    toolchain_root = "@llvm_toolchain_llvm//"
    llvm_dist_label = Label(toolchain_root + ":BUILD.bazel")
    llvm_dist_path_prefix = _pkg_path_from_label(llvm_dist_label)
    llvm_dist_rel_path = _canonical_dir_path("../../" + llvm_dist_path_prefix)
    llvm_dist_label_prefix = toolchain_root + ":"

    wrapper_bin_prefix = "bin/"
    tools_path_prefix = "bin/"
    for tool_name in _toolchain_tools:
        rctx.symlink(llvm_dist_rel_path + "bin/" + tool_name, tools_path_prefix + tool_name)

    rctx.file(
        "BUILD.bazel",
        content = rctx.read(Label("//cc/toolchain:BUILD.toolchain")),
        executable = False,
    )

    rctx.file(
        "bin/cc_wrapper.sh",
        content = rctx.read(Label("//cc/toolchain:cc_wrapper.sh")),
        executable = True,
    )

    rctx.file(
        "bin/host_libtool_wrapper.sh",
        content = rctx.read(Label("//cc/toolchain:host_libtool_wrapper.sh")),
        executable = True,
    )

    return None

llvm = repository_rule(
    local = False,
    implementation = _llvm_repo_impl,
)

toolchain = repository_rule(
    local = True,
    configure = True,
    implementation = _toolchain_impl,
)

LLVM_DISTRIBUTION_URL = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz"

def swift_cc_toolchain():
    if "x86_64-linux-gnu-llvm-distribution-14" not in native.existing_rules():
        http_archive(
            name = "x86_64-linux-gnu-llvm-distribution-14",
            build_file = Label("//cc/toolchain:BUILD.llvm_repo"),
            url = LLVM_DISTRIBUTION_URL,
            strip_prefix = "clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04",
        )
