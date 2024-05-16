# github_release_asset_file: Like http_file(), but works with GitHub
# release assets.
#
# Created because downloading private release assets from GitHub is a PITA.

load(":github_release_context.bzl", "github_release_context")

def _impl(ctx):
    downloaded_file_path = ctx.attr.downloaded_file_path if ctx.attr.downloaded_file_path else ctx.attr.asset_name

    # Create file/ directory
    ctx.file("file/.sentinel", "")

    # Download file to file/ directory
    gh = github_release_context(ctx)
    gh.download(
        gh,
        owner = ctx.attr.owner,
        repo = ctx.attr.repo,
        tag_name = ctx.attr.tag_name,
        asset_name = ctx.attr.asset_name,
        sha256 = ctx.attr.sha256,
        netrc = ctx.attr.netrc,
        executable = ctx.attr.executable,
        output = "file/{}".format(downloaded_file_path),
    )

    # Define workspace and build files so that @repository//file works
    ctx.file("WORKSPACE", "workspace(name = \"{name}\")".format(name = ctx.name))
    ctx.file("file/BUILD.bazel", """
filegroup(
    name = "file",
    srcs = ["{downloaded_file_path}"],
    visibility = ["//visibility:public"],
)
""".format(downloaded_file_path = downloaded_file_path))
    return None

github_release_asset_file = repository_rule(
    _impl,
    attrs = {
        "owner": attr.string(
            mandatory = True,
            doc = "The GitHub repo owner (my_org in https://github.com/my_org/my_private_ruleset)",
        ),
        "repo": attr.string(
            mandatory = True,
            doc = "The GitHub repo name (my_private_ruleset in https://github.com/my_org/my_private_ruleset)",
        ),
        "tag_name": attr.string(
            mandatory = True,
            doc = "The name of the tag associated with the GitHub release",
        ),
        "asset_name": attr.string(
            mandatory = True,
            doc = "The name of the asset contained within the GitHub release to download",
        ),
        "sha256": attr.string(
            doc = "The expected SHA256 checksum of the downloaded GitHub release asset",
        ),
        "netrc": attr.string(
            doc = "Location of the .netrc file to use for authentication",
        ),
        "downloaded_file_path": attr.string(
            doc = "Path assigned to the file downloaded (defaults to asset_name)",
        ),
        "executable": attr.bool(
            default = False,
            doc = "Mark the downloaded file as executable",
        )
    },
)
