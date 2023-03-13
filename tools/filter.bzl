def _filter_impl(ctx):
    return DefaultInfo(files = depset([f for f in ctx.files.srcs if f.extension == ctx.attr.extension]))

filter = rule(
    implementation = _filter_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True, mandatory = True),
        "extension": attr.string(mandatory = True),
    },
)

def filter_srcs(name, srcs):
    filter(name = name, srcs = srcs, extension = "c")

def filter_hdrs(name, srcs):
    filter(name = name, srcs = srcs, extension = "h")

def filter_libs(name, srcs):
    filter(name = name, srcs = srcs, extension = "a")
