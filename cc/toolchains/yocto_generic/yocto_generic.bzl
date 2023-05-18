def _remove_all_occurence(list, e):
    for _ in range(len(list)):
        if e in list:
            list.remove(e)
        else:
            break

    return list

def _get_cc(environ):
    cc_env = environ["CC"].split(" ")
    return cc_env[0], cc_env[1:]

def _get_cflags(environ):
    cflags = environ["CFLAGS"].split(" ")

    if "-O2" in cflags:
        cflags.remove("-O2")
    if "-g" in cflags:
        cflags.remove("-g")

    return cflags

def _yocto_generic_impl(repository_ctx):
    repository_ctx.file("BUILD", executable = False)

    environ = repository_ctx.os.environ

    envs = [
        "CC",
        "CXX",
        "CPP",
        "AS",
        "LD",
        "STRIP",
        "RANLIB",
        "OBJCOPY",
        "OBJDUMP",
        "AR",
        "NM",
        "SDKTARGETSYSROOT",
        "OECORE_NATIVE_SYSROOT",
    ]

    for env in envs:
        if env not in environ:
            repository_ctx.file(
                "toolchain.bzl",
                """
CC = ""
CXX = ""
CPP = ""
AS = ""
LD = ""
STRIP = ""
RANLIB = ""
OBJCOPY = ""
OBJDUMP = ""
AR = ""
NM = ""
COMPILE_FLAGS = []
LINK_FLAGS = []
SYSROOT = ""
NATIVE_INCLUDE_PATHS = []
            """,
            )
            return

    native_sysroot = environ["OECORE_NATIVE_SYSROOT"]
    include_fixed_res = repository_ctx.execute(["find", native_sysroot, "-name", "include-fixed"])
    include_fixed_list = include_fixed_res.stdout.split("\n")

    if include_fixed_res.return_code != 0 and len(include_fixed_list) != 2:
        fail("Could not find include-fixed in " + native_sysroot)

    include_fixed = include_fixed_list[0]
    include = include_fixed.removesuffix("-fixed")

    cc, compile_flags = _get_cc(environ)
    cflags = _get_cflags(environ)
    ldflags = environ["LDFLAGS"].split(" ")

    repository_ctx.file(
        "toolchain.bzl",
        """
CC = "{CC}"
CXX = "{CXX}"
CPP = "{CPP}"
AS = "{AS}"
LD = "{LD}"
STRIP = "{STRIP}"
RANLIB = "{RANLIB}"
OBJCOPY = "{OBJCOPY}"
OBJDUMP = "{OBJDUMP}"
AR = "{AR}"
NM = "{NM}"
COMPILE_FLAGS = {COMPILE_FLAGS}
LINK_FLAGS = {LINK_FLAGS}
SYSROOT = "{SYSROOT}"
NATIVE_INCLUDE_PATHS = {NATIVE_INCLUDE_PATHS}
""".format(
            CC = repository_ctx.which(cc),
            CXX = repository_ctx.which(environ["CXX"].split(" ")[0]),
            CPP = repository_ctx.which(environ["CPP"].split(" ")[0]),
            AS = repository_ctx.which(environ["AS"].split(" ")[0]),
            LD = repository_ctx.which(environ["LD"].split(" ")[0]),
            STRIP = repository_ctx.which(environ["STRIP"]),
            RANLIB = repository_ctx.which(environ["RANLIB"]),
            OBJCOPY = repository_ctx.which(environ["OBJCOPY"]),
            OBJDUMP = repository_ctx.which(environ["OBJDUMP"]),
            AR = repository_ctx.which(environ["AR"]),
            NM = repository_ctx.which(environ["NM"]),
            COMPILE_FLAGS = _remove_all_occurence(compile_flags + cflags, ""),
            LINK_FLAGS = _remove_all_occurence(compile_flags + ldflags, ""),
            SYSROOT = environ["SDKTARGETSYSROOT"],
            NATIVE_INCLUDE_PATHS = [include_fixed, include],
        ),
    )

yocto_generic = repository_rule(
    implementation = _yocto_generic_impl,
    environ = [
        "CXX",
        "CPP",
        "AS",
        "LD",
        "STRIP",
        "RANLIB",
        "OBJCOPY",
        "OBJDUMP",
        "AR",
        "NM",
        "SDKTARGETSYSROOT",
    ],
    attrs = {},
)
