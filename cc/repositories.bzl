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

llvm = repository_rule(
    local = False,
    implementation = _llvm_repo_impl
)

def swift_cc_toolchain():
    print("HELLO WORLD")
    # remember this is hardcoded in the toolchain BUILD file.
    llvm(name = "llvm_toolchain_llvm")
    native.register_toolchains(
        "//cc/toolchain:cc-toolchain-x86_64-linux",
    )
