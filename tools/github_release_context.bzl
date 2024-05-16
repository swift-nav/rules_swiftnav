# github_release_context.bzl: A "class" which allows multiple rules to share
# code for downloading GitHub release assets
#
# Example usage:
#   gh = github_release_context(repository_ctx)
#   gh.download(gh, owner, repo, tag_name, asset_name, output)

load(
    "@bazel_tools//tools/build_defs/repo:utils.bzl",
    "read_netrc",
    "read_user_netrc",
    "use_netrc",
)

def _calculate_sha256(gh, file):
    """Calculates the sha256 hash of a file"""
    res = gh.execute(["sha256sum", file])
    if res.return_code != 0:
        fail("sha256sum failed: " + res.stderr)
    actual_sha256 = res.stdout.split(" ")[0]
    return actual_sha256

def _download_ex(gh, url, output, executable = False, sha256 = "", headers = {}):
    """Simplified repository_ctx.download() with support for specifying custom
    HTTP request headers."""
    if not gh.which("curl"):
        fail("curl binary not found")

    args = ["curl", "--silent", "-o", output, "--write-out", "%{http_code}", "--location"]
    for k, v in headers.items():
        args.extend(["-H", "{k}: {v}".format(k = k, v = v)])
    args.append(url)
    res = gh.execute(args)
    if res.return_code != 0:
        fail("curl failed: " + res.stderr)

    http_response_code = int(res.stdout)
    if http_response_code < 200 or http_response_code > 299:
        fail("Download of {url} failed with HTTP response code {http_response_code}".format(
            url = url,
            http_response_code = http_response_code
        ))

    actual_sha256 = gh._calculate_sha256(gh, output)
    if sha256 and actual_sha256 != sha256:
        fail("sha256 mismatch: expected {} actual {}".format(sha256, actual_sha256))

    if executable:
        res = gh.execute(["chmod", "+x", output])
        if res.return_code != 0:
            fail("marking file executable failed: " + res.stderr)

    return struct(
        success = True,
        sha256 = actual_sha256,
    )

def _get_github_auth_token(gh, netrc):
    """Gets the github auth token from ~/.netrc"""
    if netrc:
        netrc = read_netrc(gh, netrc)
    elif "NETRC" in gh.os.environ:
        netrc = read_netrc(gh, gh.os.environ["NETRC"])
    else:
        netrc = read_user_netrc(gh)

    for host in ["github.com", "api.github.com"]:
        url = "https://{host}/".format(host = host)
        auth_dict = use_netrc(netrc, [url], {host: "Bearer <password>"})
        if auth_dict:
            return auth_dict[url]["password"]

    fail("""Could not find GitHub auth token.  Add the following line to your ~/.netrc:

machine github.com password ghp_...

Where ghp_... is a GitHub personal access token with permissions to download release assets.
""")

def _get_github_release_id(gh, owner, repo, tag_name, auth_token):
    """Gets the release id of a GitHub release"""
    releases_file = "releases.json"
    gh._download_ex(
        gh,
        url = "https://api.github.com/repos/{owner}/{repo}/releases".format(
            owner = owner,
            repo = repo),
        output = releases_file,
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer {auth_token}".format(auth_token = auth_token),
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    releases = json.decode(gh.read(releases_file))
    gh.delete(releases_file)
    for release in releases:
        if release["tag_name"] == tag_name:
            return release["id"]
    fail("Could not find release with tag {tag_name} in {owner}/{repo}".format(
        tag_name = tag_name,
        owner = owner,
        repo = repo))

def _get_github_release_asset_id(gh, owner, repo, release_id, asset_name, auth_token):
    """Gets the asset id of an asset within a GitHub release"""
    assets_file = "assets.json"
    gh._download_ex(
        gh,
        url = "https://api.github.com/repos/{owner}/{repo}/releases/{release_id}/assets".format(
            owner = owner,
            repo = repo,
            release_id = release_id),
        output = assets_file,
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer {auth_token}".format(auth_token = auth_token),
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    assets = json.decode(gh.read(assets_file))
    gh.delete(assets_file)
    for asset in assets:
        if asset["name"] == asset_name:
            return asset["id"]
    fail("Could not find asset named {asset_name} in {owner}/{repo} release {release_id}".format(
        asset_name = asset_name,
        owner = owner,
        repo = repo,
        release_id = release_id))

def _download_with_http_client(gh, owner, repo, tag_name, asset_name, output,
    executable = False, netrc = None, sha256 = ""):
    """Downloads an asset from github using HTTP requests"""
    github_auth_token = gh._get_github_auth_token(gh, netrc)

    release_id = gh._get_github_release_id(
        gh,
        owner = owner,
        repo = repo,
        tag_name = tag_name,
        auth_token = github_auth_token,
    )

    asset_id = gh._get_github_release_asset_id(
        gh,
        owner = owner,
        repo = repo,
        release_id = release_id,
        asset_name = asset_name,
        auth_token = github_auth_token,
    )

    return gh._download_ex(
        gh,
        url = "https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}".format(
            owner = owner,
            repo = repo,
            asset_id = asset_id),
        headers = {
            # Note the required use of a custom request header to download the release _content_
            "Accept": "application/octet-stream",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": "Bearer {}".format(github_auth_token),
        },
        sha256 = sha256,
        executable = executable,
        output = output,
    )

def _download(gh, owner, repo, tag_name, asset_name, output, executable = False,
    netrc = None, sha256 = ""):
    """download() that works with a GitHub release asset"""
    return gh._download_with_http_client(
        gh,
        owner = owner,
        repo = repo,
        tag_name = tag_name,
        asset_name = asset_name,
        executable = executable,
        netrc = netrc,
        sha256 = sha256,
        output = output,
    )

def _download_and_extract(gh, owner, repo, tag_name, asset_name, netrc = None,
    sha256 = "", strip_prefix = ""):
    """download_and_extract() that works with a GitHub release asset"""
    download_file = "downloaded_file.tar.gz"
    res = gh.download(
        gh,
        owner = owner,
        repo = repo,
        tag_name = tag_name,
        asset_name = asset_name,
        output = download_file,
        netrc = netrc,
        sha256 = sha256,
    )
    gh.extract(download_file, stripPrefix = strip_prefix)
    gh.delete(download_file)
    return struct(
        success = True,
        sha256 = res.sha256,
    )

def github_release_context(repository_ctx):
    return struct(
        # Private members
        _calculate_sha256 = _calculate_sha256,
        _download_ex = _download_ex,
        _get_github_auth_token = _get_github_auth_token,
        _get_github_release_id = _get_github_release_id,
        _get_github_release_asset_id = _get_github_release_asset_id,
        _download_with_http_client = _download_with_http_client,
        # Forwarding methods to repository_ctx
        delete = repository_ctx.delete,
        execute = repository_ctx.execute,
        extract = repository_ctx.extract,
        os = repository_ctx.os,
        path = repository_ctx.path,
        read = repository_ctx.read,
        which = repository_ctx.which,
        # Public members
        download = _download,
        download_and_extract = _download_and_extract,
    )
