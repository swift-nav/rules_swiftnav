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
