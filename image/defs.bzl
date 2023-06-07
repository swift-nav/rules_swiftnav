load("@rules_swiftnav//image:transition.bzl", "multi_arch")
load("@rules_oci//oci:defs.bzl", "oci_image_index")

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
        tags = ["manual"],
    )

    oci_image_index(
        name = name,
        images = [":{}".format(transition_name)],
        **kwargs
    )

def image_tag(name, value, **kwargs):
    """
    Creates a tag file from given string

    Args:
        name: Name of the tag target
        value: String that will be used as a tag
        **kwargs: Arguments passed to genrule
    """
    native.genrule(
        name = name,
        outs = ["{}.txt".format(name)],
        cmd = "echo {} > $@".format(value),
        tags = ["manual"],
        **kwargs
    )

def image_stamp_tag(name, var, **kwargs):
    """
    Creates a tag file from a given variable defined in stable-status.txt file

    Args:
        name: Name of the tag target
        var: Variable to use as a tag
        **kwargs: Arguments passed to genrule
    """
    native.genrule(
        name = name,
        outs = ["{}.txt".format(name)],
        # `(?<=A)B` in regex is a positive lookbehind - finds expression B that's preceded with A
        cmd = "cat bazel-out/stable-status.txt | grep -Po '(?<={}\\s).*' > $@".format(var),
        stamp = True,
        **kwargs
    )
