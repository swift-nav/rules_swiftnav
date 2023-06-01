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

def swift_image_index(name, image, platforms, **kwargs):
    """
    Creates a multi-arch image index

    Args:
        name: Name of the image target
        image: Label of the image
        platforms: List of platforms
        **kwargs: Arguments passed down to oci_image_index
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
        **kwargs
    )

def swift_tag(name, value, out):
    """
    Creates a tag file from given value

    Args:
        name: Name of the tag target
        value: String that will be used as a tag
        out: Output file
    """
    native.genrule(
        name = name,
        outs = [out],
        cmd = "echo {} > @$".format(value),
    )

def swift_stamp_tag(name, var, out):
    """
    Creates a tag file from a given variable defined in stable-status.txt file

    Args:
        name: Name of the tag target
        var: Variable to use as a tag
        out: Output file
    """
    native.genrule(
        name = name,
        outs = [out],
        # `(?<=A)B` in regex is a positive lookbehind - finds expression B that's preceded with A
        cmd = "cat bazel-out/stable-status.txt | grep -Po '(?<={}\\s).*' > $@".format(var),
        stamp = True,
    )
