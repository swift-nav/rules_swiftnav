load(":lfs.bzl", "lfs_file")

def _lfs_repo_impl(rctx):
    build = 'load("@rules_swiftnav//lfs:lfs.bzl", "lfs_runfile")\n\n'
    for name, actual in sorted(rctx.attr.aliases.items()):
        build += 'alias(name = "%s", actual = "%s", visibility = ["//visibility:public"])\n' % (name, actual)
    for name, src in sorted(rctx.attr.lfs_files.items()):
        build += 'lfs_runfile(name = "%s", src = "%s", path = "%s/%s", visibility = ["//visibility:public"])\n' % (name, src, rctx.attr.path, name)
    rctx.file("BUILD.bazel", build)
    return rctx.repo_metadata(
        reproducible = True,
    )

_lfs_repo = repository_rule(
    implementation = _lfs_repo_impl,
    attrs = {
        "path": attr.string(mandatory = True),
        "aliases": attr.string_dict(),
        "lfs_files": attr.string_dict(),
    },
)

def _walk_directory(root):
    files = []
    stack = [root]

    # Starlark has no recursion or while loops, so walk with a bounded loop.
    for _ in range(1000000):
        if not stack:
            break
        directory = stack.pop()
        for entry in directory.readdir():
            if entry.is_dir:
                stack.append(entry)
            else:
                files.append(entry)
    if stack:
        fail("lfs: too many directories below %s" % root)

    return sorted(files, key = str)

_SPEC = "version https://git-lfs.github.com/spec/v1"

def _oid(mctx, file):
    mctx.watch(file)
    head = mctx.execute(["head", "-c", "100", str(file)]).stdout
    if head.startswith(_SPEC):
        for line in mctx.read(file).splitlines():
            if line.startswith("oid sha256:"):
                return line[len("oid sha256:"):]
        fail("lfs: no oid found in %s" % file)
    return None

def _lfs_impl(mctx):
    declared = {}
    for module in mctx.modules:
        for tag in module.tags.dir:
            if tag.package and not tag.path.startswith(tag.package + "/"):
                fail("lfs: path %s is not below package %s" % (tag.path, tag.package))

            # walk below path for each file and then call lfs_file
            workspace = mctx.path(Label("@@//:MODULE.bazel")).dirname
            root = workspace.get_child(tag.path)
            files = _walk_directory(root)
            aliases = {}
            lfs_files = {}
            for file in files:
                oid = _oid(mctx, file)
                rel = str(file)[len(str(root)) + 1:]
                if not oid:
                    # Plain or already smudged file: use the checked-out copy.
                    aliases[rel] = "@@//%s:%s/%s" % (tag.package, tag.path[len(tag.package):].lstrip("/"), rel)
                    continue
                repo = "lfs_" + oid
                if repo not in declared:
                    declared[repo] = file.basename
                    lfs_file(
                        name = repo,
                        oid = oid,
                        basename = file.basename,
                        lfs_url = tag.lfs_url,
                    )
                lfs_files[rel] = "@%s//file:%s" % (repo, declared[repo])

            _lfs_repo(name = tag.name, path = tag.path, aliases = aliases, lfs_files = lfs_files)

    return mctx.extension_metadata(
        reproducible = True,
    )

_dir_tag = tag_class(
    attrs = {
        "name": attr.string(mandatory = True),
        "path": attr.string(mandatory = True),
        "lfs_url": attr.string(mandatory = True),
        "package": attr.string(default = ""),
    },
)

lfs = module_extension(
    implementation = _lfs_impl,
    tag_classes = {
        "dir": _dir_tag,
    },
)
