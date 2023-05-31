load("@rules_swiftnav//image:transition.bzl", "multi_arch")
load("@rules_pkg//:pkg.bzl", "pkg_tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_image_index")

def swift_image(name, bin = [], external_data = [], tars = [], **kwargs):
    actual_tars = []

    if bin:
        tar_name = "{}_binary_tar".format(name)
        pkg_tar(
            name = tar_name,
            srcs = bin,
            package_dir = "/app/bin",
            tags = ["manual"],
        )
        actual_tars.append(tar_name)

    if external_data:
        tar_name = "{}_external_data_tar".format(name)
        pkg_tar(
            name = tar_name,
            srcs = external_data,
            package_dir = "/app/external_data",
            tags = ["manual"],
        )
        actual_tars.append(tar_name)

    actual_tars += tars

    oci_image(
        name = name,
        tars = actual_tars,
        **kwargs
    )

def swift_image_index(name, image, platforms, tags = [], visibility = None, **kwargs):
    """Creates a multi-arch image index

    Args:
        name: Name of the image target
        image: Label of the image
        platforms: List of platforms
        tags: Tags
        visibility: Visibility modifier
        **kwargs: Arguments passed down to oci_image
    """
    transition_name = "{}_transition".format(name)

    multi_arch(
        name = transition_name,
        image = image,
        platforms = platforms,
    )

    oci_image_index(
        name = name,
        images = [":{}".format(transition_name)],
        visibility = visibility,
        tags = tags,
    )

def swift_image_tag(name, out):
    native.genrule(
        name = name,
        outs = [out],
        cmd = select({
            # Read STABLE_GIT_VERSION's value from stable-status.txt
            # `(?<=A)B` in regex is a positive lookbehind - finds expression B that's preceded with A
            "@rules_swiftnav//image:_stamp": "cat bazel-out/stable-status.txt | grep -Po '(?<=STABLE_GIT_VERSION\\s).*' > $@",
            "@rules_swiftnav//image:_latest_master": "latest-master",
            "//conditions:default": "echo test > $@",
        }),
        stamp = True,
    )
