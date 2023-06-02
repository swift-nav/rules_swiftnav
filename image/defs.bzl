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
    )

    oci_image_index(
        name = name,
        images = [":{}".format(transition_name)],
        **kwargs
    )

def image_tag(name, tag):
    """
    Creates a tag file from given string

    Args:
        name: Name of the tag target
        tag: String that will be used as a tag
    """
    native.genrule(
        name = name,
        outs = ["{}.txt".format(name)],
        cmd = "echo {} > $@".format(tag),
    )

def image_stamp_tag(name, var):
    """
    Creates a tag file from a given variable defined in stable-status.txt file

    Args:
        name: Name of the tag target
        var: Variable to use as a tag
    """
    native.genrule(
        name = name,
        outs = ["{}.txt".format(name)],
        # `(?<=A)B` in regex is a positive lookbehind - finds expression B that's preceded with A
        cmd = "cat bazel-out/stable-status.txt | grep -Po '(?<={}\\s).*' > $@".format(var),
        stamp = True,
    )
