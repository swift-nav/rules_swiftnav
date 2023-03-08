# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""
netcdf-c@4.9.0
"""

load("@bazel_skylib//lib:selects.bzl", "selects")
load("@rules_swiftnav//tools:configure_file.bzl", "configure_file")
load("@rules_swiftnav//third_party/netcdf-c:aarch64-darwin-config.bzl", "AARCH64_DARWIN_CONFIG")
load("@rules_swiftnav//third_party/netcdf-c:x86_64-darwin-config.bzl", "X86_64_DARWIN_CONFIG")
load("@rules_swiftnav//third_party/netcdf-c:x86_64-linux-config.bzl", "X86_64_LINUX_CONFIG")
load("@rules_swiftnav//third_party/netcdf-c:attr.bzl", "attr")
load("@rules_swiftnav//third_party/netcdf-c:ncx.bzl", "ncx")
load("@rules_swiftnav//third_party/netcdf-c:putget.bzl", "putget")

selects.config_setting_group(
    name = "aarch64-darwin",
    match_all = [
        "@platforms//cpu:aarch64",
        "@platforms//os:macos",
    ],
)

selects.config_setting_group(
    name = "x86_64-darwin",
    match_all = [
        "@platforms//cpu:x86_64",
        "@platforms//os:macos",
    ],
)

selects.config_setting_group(
    name = "x86_64-linux",
    match_all = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
)

configure_file(
    name = "netcdf_dispatch",
    out = "netcdf_dispatch.h",
    template = "include/netcdf_dispatch.h.in",
    vars = {
        "NC_DISPATCH_VERSION": "5",
    },
)

configure_file(
    name = "netcdf_meta",
    out = "netcdf_meta.h",
    template = "include/netcdf_meta.h.in",
    vars = {
        "NC_VERSION_MAJOR": "4",  # /*!< netcdf-c major version. */
        "NC_VERSION_MINOR": "9",  # /*!< netcdf-c minor version. */
        "NC_VERSION_PATCH": "0",  # /*!< netcdf-c patch version. */
        "NC_VERSION_NOTE": "",  # /*!< netcdf-c note. May be blank. */
        "NC_VERSION": "4.9.0",
        "NC_HAS_NC2": "1",  # /*!< API version 2 support. */
        "NC_HAS_NC4": "1",  # /*!< API version 4 support. */
        "NC_HAS_HDF4": "0",  # /*!< HDF4 support. */
        "NC_HAS_HDF5": "1",  # /*!< HDF5 support. */
        "NC_HAS_SZIP": "1",  # /*!< szip support (HDF5 only) */
        "NC_HAS_SZIP_WRITE": "1",  # /*!< szip write support (HDF5 only) */
        "NC_HAS_DAP2": "0",  # /*!< DAP2 support. */
        "NC_HAS_DAP4": "0",  # /*!< DAP4 support. */
        "NC_HAS_BYTERANGE": "0",  # /*!< Byterange support. */
        "NC_HAS_DISKLESS": "1",  # /*!< diskless support. */
        "NC_HAS_MMAP": "1",  # /*!< mmap support. */
        "NC_HAS_JNA": "0",  # /*!< jna support. */
        "NC_HAS_PNETCDF": "0",  # /*!< PnetCDF support. */
        "NC_HAS_PARALLEL4": "0",  # /*!< parallel IO support via HDF5 */
        "NC_HAS_PARALLEL": "0",  # /*!< parallel IO support via HDF5 and/or PnetCDF. */
        "NC_HAS_CDF5": "1",  # /*!< CDF5 support. */
        "NC_HAS_ERANGE_FILL": "1",  # /*!< ERANGE_FILL Support. */
        "NC_RELAX_COORD_BOUND": "1",  # /*!< Always allow 0 counts in parallel I/O. */
        "NC_DISPATCH_VERSION": "5",  # /*!< Dispatch table version. */
        "NC_HAS_PAR_FILTERS": "1",  # /* Parallel I/O with filter support. */
        "NC_HAS_NCZARR": "0",  # /*!< Parallel I/O with filter support. */
        "NC_HAS_MULTIFILTERS": "1",  # /*!< Nczarr support. */
        "NC_HAS_LOGGING": "0",  # /*!< Logging support. */
        "NC_HAS_QUANTIZE": "1",  # /*!< Quantization support. */
        "NC_HAS_ZSTD": "0",  # /*!< Zstd support. */
        "NC_HAS_BENCHMARKS": "0",  # /*!< Benchmarks. */
    },
)

hdrs = [
    ":config",
    ":netcdf_dispatch",
    ":netcdf_meta",
    "include/ceconstraints.h",
    "include/err_macros.h",
    "include/fbits.h",
    "include/hdf4dispatch.h",
    "include/hdf5dispatch.h",
    "include/hdf5internal.h",
    "include/isnan.h",
    "include/nc3dispatch.h",
    "include/nc3internal.h",
    "include/nc4dispatch.h",
    "include/nc4internal.h",
    "include/ncauth.h",
    "include/ncbytes.h",
    "include/ncconfigure.h",
    "include/nccrc.h",
    "include/ncdap.h",
    "include/ncdimscale.h",
    "include/ncdispatch.h",
    "include/ncexhash.h",
    "include/ncexternl.h",
    "include/nc.h",
    "include/nchashmap.h",
    "include/nchttp.h",
    "include/ncindex.h",
    "include/ncjson.h",
    "include/nclist.h",
    "include/nc_logging.h",
    "include/nclog.h",
    "include/ncmodel.h",
    "include/ncoffsets.h",
    "include/ncpathmgr.h",
    "include/nc_provenance.h",
    "include/ncrc.h",
    "include/ncs3sdk.h",
    "include/nctestserver.h",
    "include/nc_tests.h",
    "include/nctime.h",
    "include/ncuri.h",
    "include/ncutf8.h",
    "include/ncxcache.h",
    "include/ncxml.h",
    "include/netcdf_aux.h",
    "include/netcdf_f.h",
    "include/netcdf_filter_build.h",
    "include/netcdf_filter.h",
    "include/netcdf_filter_hdf5_build.h",
    "include/netcdf.h",
    "include/netcdf_json.h",
    "include/netcdf_mem.h",
    "include/netcdf_par.h",
    "include/onstack.h",
    "include/rnd.h",
    "include/XGetopt.h",
]

genrule(
    name = "config",
    outs = ["config.h"],
    cmd = select(
        {
            ":aarch64-darwin": "cat <<'EOF' > $@ {}EOF".format(AARCH64_DARWIN_CONFIG),
            ":x86_64-darwin": "cat <<'EOF' > $@ {}EOF".format(X86_64_DARWIN_CONFIG),
            ":x86_64-linux": "cat <<'EOF' > $@ {}EOF".format(X86_64_LINUX_CONFIG),
        },
        no_match_error = "Currently only aarch64-darwin, x86_64-darwin, and x86_64-linux are supported.",
    ),
)

genrule(
    name = "attr",
    outs = ["attr.c"],
    cmd = "cat <<'EOF' > $@ {}EOF".format(attr),
)

genrule(
    name = "ncx",
    outs = ["ncx.c"],
    cmd = "cat <<'EOF' > $@ {}EOF".format(ncx),
)

genrule(
    name = "putget",
    outs = ["putget.c"],
    cmd = "cat <<'EOF' > $@ {}EOF".format(putget),
)

dispatch_srcs = [
    "libdispatch/datt.c",
    "libdispatch/dattget.c",
    "libdispatch/dattinq.c",
    "libdispatch/dattput.c",
    "libdispatch/dauth.c",
    "libdispatch/daux.c",
    "libdispatch/dcompound.c",
    "libdispatch/dcopy.c",
    "libdispatch/dcrc32.c",
    "libdispatch/dcrc32.h",
    "libdispatch/dcrc64.c",
    "libdispatch/ddim.c",
    "libdispatch/ddispatch.c",
    "libdispatch/denum.c",
    "libdispatch/derror.c",
    "libdispatch/dfile.c",
    "libdispatch/dfilter.c",
    "libdispatch/dgroup.c",
    "libdispatch/dinfermodel.c",
    "libdispatch/dinstance.c",
    "libdispatch/dinternal.c",
    "libdispatch/dnotnc3.c",
    "libdispatch/dnotnc4.c",
    "libdispatch/doffsets.c",
    "libdispatch/dopaque.c",
    "libdispatch/dparallel.c",
    "libdispatch/dpathmgr.c",
    "libdispatch/drc.c",
    "libdispatch/dreadonly.c",
    "libdispatch/ds3util.c",
    "libdispatch/dstring.c",
    "libdispatch/dtype.c",
    "libdispatch/dutf8.c",
    "libdispatch/dutil.c",
    "libdispatch/dvar.c",
    "libdispatch/dvarget.c",
    "libdispatch/dvarinq.c",
    "libdispatch/dvarput.c",
    "libdispatch/dvlen.c",
    "libdispatch/nc.c",
    "libdispatch/ncbytes.c",
    "libdispatch/ncexhash.c",
    "libdispatch/nchashmap.c",
    "libdispatch/ncjson.c",
    "libdispatch/nclist.c",
    "libdispatch/nclistmgr.c",
    "libdispatch/nclog.c",
    "libdispatch/nctime.c",
    "libdispatch/ncuri.c",
    "libdispatch/ncxcache.c",
    "libdispatch/utf8proc.c",
    "libdispatch/utf8proc.h",
]

dispatch_textual_hdrs = [
    "libdispatch/utf8proc_data.c",
]

netcdf3_srcs = [
    "libsrc/dim.c",
    "libsrc/lookup3.c",
    "libsrc/memio.c",
    "libsrc/mmapio.c",
    "libsrc/nc3dispatch.c",
    "libsrc/nc3internal.c",
    "libsrc/ncio.c",
    "libsrc/ncio.h",
    "libsrc/ncx.h",
    "libsrc/posixio.c",
    "libsrc/pstdint.h",
    "libsrc/v1hpg.c",
    "libsrc/var.c",
    ":attr",
    ":ncx",
    ":putget",
]

netcdf4_srcs = [
    "libsrc4/nc4attr.c",
    "libsrc4/nc4cache.c",
    "libsrc4/nc4dim.c",
    "libsrc4/nc4dispatch.c",
    "libsrc4/nc4grp.c",
    "libsrc4/nc4internal.c",
    "libsrc4/nc4type.c",
    "libsrc4/nc4var.c",
    "libsrc4/ncfunc.c",
    "libsrc4/ncindex.c",
]

netcdfhdf5_srcs = [
    "libhdf5/hdf5attr.c",
    "libhdf5/hdf5create.c",
    "libhdf5/hdf5debug.c",
    "libhdf5/hdf5debug.h",
    "libhdf5/hdf5dim.c",
    "libhdf5/hdf5dispatch.c",
    "libhdf5/hdf5err.h",
    "libhdf5/hdf5file.c",
    "libhdf5/hdf5filter.c",
    "libhdf5/hdf5grp.c",
    "libhdf5/hdf5internal.c",
    "libhdf5/hdf5open.c",
    "libhdf5/hdf5set_format_compatibility.c",
    "libhdf5/hdf5type.c",
    "libhdf5/hdf5var.c",
    "libhdf5/nc4hdf.c",
    "libhdf5/nc4info.c",
    "libhdf5/nc4mem.c",
    "libhdf5/nc4memcb.c",
]

cc_library(
    name = "netcdf-c",
    srcs = dispatch_srcs + netcdf3_srcs + netcdf4_srcs + netcdfhdf5_srcs + [
        "liblib/nc_initialize.c",
    ],
    hdrs = hdrs,
    defines = ["HAVE_CONFIG_H"],
    # Allows including <config.h> with angle brackets
    include_prefix = ".",
    includes = [
        "include",
        "libdispatch",
        "libsrc",
    ],
    textual_hdrs = dispatch_textual_hdrs,
    visibility = ["//visibility:public"],
    deps = [
        "@hdf5",
    ],
)
