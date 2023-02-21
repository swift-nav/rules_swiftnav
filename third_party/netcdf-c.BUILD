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

load("@rules_swiftnav//tools:configure_file.bzl", "configure_file")

configure_file(
    name = "expand_netcdf_dispatch_h_in",
    out = "netcdf_dispatch.h",
    template = "include/netcdf_dispatch.h.in",
    vars = {
        "NC_DISPATCH_VERSION": "5",
    },
)

configure_file(
    name = "expand_netcdf_meta_h_in",
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
    ":gen_config_h",
    ":expand_netcdf_dispatch_h_in",
    ":expand_netcdf_meta_h_in",
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

defines = [
    "HAVE_CONFIG_H",
]

cc_library(
    name = "netcdf-c",
    srcs = [
        "liblib/nc_initialize.c",
        ":dispatch",
        ":netcdf3",
        ":netcdf4",
        ":netcdfhdf5",
    ],
    hdrs = hdrs,
    defines = defines,
    includes = ["include"],
    visibility = ["//visibility:public"],
    deps = ["@hdf5"],
)

cc_library(
    name = "dispatch",
    srcs = [
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
    ],
    hdrs = hdrs,
    defines = defines,
    includes = [
        "include",
        "libdispatch",
    ],
    textual_hdrs = [
        # breaks build because of undefined type
        "libdispatch/utf8proc_data.c",
    ],
    deps = ["@hdf5"],
)

genrule(
    name = "gen_attr_c",
    srcs = ["libsrc/attr.m4"],
    outs = ["attr.c"],
    cmd = "m4 $(SRCS) > $@",
)

genrule(
    name = "gen_ncx_c",
    srcs = ["libsrc/ncx.m4"],
    outs = ["ncx.c"],
    cmd = "m4 $(SRCS) > $@",
)

genrule(
    name = "gen_putget_c",
    srcs = ["libsrc/putget.m4"],
    outs = ["putget.c"],
    cmd = "m4 $(SRCS) > $@",
)

cc_library(
    name = "netcdf3",
    srcs = [
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
        ":gen_attr_c",
        ":gen_ncx_c",
        ":gen_putget_c",
    ],
    hdrs = hdrs,
    defines = defines,
    # Allows including <config.h> with angle brackets
    include_prefix = ".",
    includes = [
        "include",
        "libsrc",
    ],
)

cc_library(
    name = "netcdf4",
    srcs = [
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
    ],
    hdrs = hdrs,
    defines = defines,
    includes = ["include"],
    deps = ["@hdf5"],
)

cc_library(
    name = "netcdfhdf5",
    srcs = [
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
    ],
    hdrs = hdrs,
    defines = defines,
    includes = ["include"],
    deps = ["@hdf5"],
)

genrule(
    name = "gen_config_h",
    outs = ["config.h"],
    cmd = r"""
cat <<'EOF' > $@
/*! \file

Copyright 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002,
2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014,
2015, 2016, 2017, 2018
University Corporation for Atmospheric Research/Unidata.

See \ref copyright file for more info.

*/
#ifndef CONFIG_H
#define CONFIG_H

#ifdef _MSC_VER

/* Prevent an issue where there is a circular inclusion
   of winsock.h/windows.h.  This weird state occurs with
   libdap4 and hdf4 support. The solution comes from the
   following URL, found after a bit of research.

   Added in support of the 4.5.0-rc1.  Hello, future generations.

   * https://stackoverflow.com/questions/1372480/c-redefinition-header-files-winsock2-h

   */

/* #undef HAVE_WINSOCK2_H */

#ifdef HAVE_WINSOCK2_H
   #define _WINSOCKAPI_
#endif
*/
   #if _MSC_VER>=1900
     #define STDC99
   #endif
/* Define O_BINARY so that the appropriate flags
are set when opening a binary file on Windows. */

/* Disable a few warnings under Visual Studio, for the
   time being. */
   #include <io.h>
   #pragma warning( disable: 4018 4996 4244 4305 )
   #define unlink _unlink
   #define open _open
   #define close _close
   #define read _read
   #define lseek _lseeki64

   #ifndef __clang__
   #define fstat _fstat64
   #endif

   #define off_t __int64
   #define _off_t __int64

   #ifndef _OFF_T_DEFINED
   #define _OFF_T_DEFINED
   #endif

   #define strdup _strdup
   #define fdopen _fdopen
   #define write _write
   #define strtoll _strtoi64
#endif /*_MSC_VER */

/* #undef const */

#ifndef _FILE_OFFSET_BITS
/* #undef _FILE_OFFSET_BITS */
/* #undef _LARGEFILE64_SOURCE */
/* #undef _LARGEFILE_SOURCE */
#endif

/* Define if building universal (internal helper macro) */
/* #undef AC_APPLE_UNIVERSAL_BUILD */

/* If true, will attempt to download and build netcdf-fortran. */
/* #undef BUILD_FORTRAN */

/* default file chunk cache nelems. */
#define CHUNK_CACHE_NELEMS 4133

/* default file chunk cache preemption policy. */
#define CHUNK_CACHE_PREEMPTION 0.75

/* default file chunk cache size in bytes. */
#define CHUNK_CACHE_SIZE 16777216

/* default nczarr chunk cache size in bytes. */
#define CHUNK_CACHE_SIZE_NCZARR 4194304

/* Define to one of `_getb67', `GETB67', `getb67' for Cray-2 and Cray-YMP
   systems. This function is required for `alloca.c' support on those systems.
   */
/* #undef CRAY_STACKSEG_END */

/* Define to 1 if using `alloca.c'. */
/* #undef C_ALLOCA */

/* num chunks in default per-var chunk cache. */
#define DEFAULT_CHUNKS_IN_CACHE 10

/* default chunk size in bytes */
#define DEFAULT_CHUNK_SIZE 16777216

/* set this only when building a DLL under MinGW */
/* #undef DLL_EXPORT */

/* set this only when building a DLL under MinGW */
/* #undef DLL_NETCDF */

/* if true, use atexist */
#define ENABLE_ATEXIT_FINALIZE 1

/* if true, build byte-range Client */
/* #undef ENABLE_BYTERANGE */

/* if true, use hdf5 S3 virtual file reader */
/* #undef ENABLE_HDF5_ROS3 */

/* if true, enable CDF5 Support */
#define ENABLE_CDF5 1

/* if true, enable client side filters */
/* #undef ENABLE_CLIENT_FILTERS */

/* if true, enable strict null byte header padding. */
/* #undef USE_STRICT_NULL_BYTE_HEADER_PADDING */

/* if true, build DAP2 and DAP4 Client */
/* #undef ENABLE_DAP */

/* if true, build DAP4 Client */
/* #undef ENABLE_DAP4 */

/* if true, do remote tests */
#define ENABLE_DAP_REMOTE_TESTS 1

/* if true, enable NCZARR */
/* #undef ENABLE_NCZARR */

/* if true, enable nczarr filter support */
/* #undef ENABLE_NCZARR_FILTERS */

/* if true, enable S3 support */
/* #undef ENABLE_NCZARR_S3 */

/* if true, enable nczarr zip support */
/* #undef ENABLE_NCZARR_ZIP */

/* if true, enable S3 testing*/
/* #undef ENABLE_NCZARR_S3_TESTS */

/* if true, S3 SDK is available */
/* #undef ENABLE_S3_SDK */

/* if true, Allow dynamically loaded plugins */
#define ENABLE_PLUGINS 1

/* if true, run extra tests which may not work yet */
/* #undef EXTRA_TESTS */

/* use HDF5 1.6 API */
/* #undef H5_USE_16_API */

/* Define to 1 if you have `alloca', as a function or macro. */
#define HAVE_ALLOCA 1

/* Define to 1 if you have <alloca.h> and it should be used (not on Ultrix). */
#define HAVE_ALLOCA_H 1

/* Define to 1 if you have the `atexit function. */
#define HAVE_ATEXIT 1

/* Define to 1 if bzip2 library available. */
#define HAVE_BZ2 1

/* Define to 1 if zstd library available. */
/* #undef HAVE_ZSTD */

/* Define to 1 if blosc library available. */
/* #undef HAVE_BLOSC */

/* Define to 1 if you have hdf5_coll_metadata_ops */
/* #undef HDF5_HAS_COLL_METADATA_OPS */

/* Is CURLINFO_RESPONSE_CODE defined */
/* #undef HAVE_CURLINFO_RESPONSE_CODE */

/* Is CURLINFO_HTTP_CODE defined */
/* #undef HAVE_CURLINFO_HTTP_CONNECTCODE */

/* Is CURLOPT_BUFFERSIZE defined */
/* #undef HAVE_CURLOPT_BUFFERSIZE */

/* Is CURLOPT_TCP_KEEPALIVE defined */
/* #undef HAVE_CURLOPT_KEEPALIVE */

/* Is CURLOPT_KEYPASSWD defined */
/* #undef HAVE_CURLOPT_KEYPASSWD */

/* Is CURLOPT_PASSWORD defined */
/* #undef HAVE_CURLOPT_PASSWORD */

/* Is CURLOPT_USERNAME defined */
/* #undef HAVE_CURLOPT_USERNAME */

/* Is LIBCURL version >= 7.66 */
/* #undef HAVE_LIBCURL_766 */

/* Define to 1 if you have the declaration of `isfinite', and to 0 if you
   don't. */
#define HAVE_DECL_ISFINITE 1

/* Define to 1 if you have the declaration of `isinf', and to 0 if you don't.
   */
#define HAVE_DECL_ISINF 1

/* Define to 1 if you have the declaration of `isnan', and to 0 if you don't.
   */
#define HAVE_DECL_ISNAN 1

/* Define to 1 if you have the <dirent.h> header file. */
#define HAVE_DIRENT_H 1

/* Define to 1 if you have the <dlfcn.h> header file. */
#define HAVE_DLFCN_H 1

/* Define to 1 if you have the <fcntl.h> header file. */
#define HAVE_FCNTL_H 1

/* Define to 1 if you have the BaseTsd.h header file. */
/* #undef HAVE_BASETSD_H */

/* Define if we have filelengthi64. */
/* #undef HAVE_FILE_LENGTH_I64 */

/* Define to 1 if you have the `fileno' function. */
#define HAVE_FILENO 1

/* Define to 1 if you have the `fsync' function. */
#define HAVE_FSYNC 1

/* Define to 1 if you have the <getopt.h> header file. */
#define HAVE_GETOPT_H 1

/* Define to 1 if you have the `getpagesize' function. */
#define HAVE_GETPAGESIZE 1

/* Define to 1 if you have the `getrlimit' function. */
#define HAVE_GETRLIMIT 1

/* Define to 1 if you have the `gettimeofday' function. */
#define HAVE_GETTIMEOFDAY 1

/* Define to 1 if you have the `clock_gettime' function. */
#define HAVE_CLOCK_GETTIME 1

/* Define to 1 if you have the `gettimeofday' function. */
/* #undef HAVE_STRUCT_TIMESPEC */

/* Define to 1 if you have the `H5Z_SZIP' function. */
#define HAVE_H5Z_SZIP 1

/* Define to 1 if you have libsz */
#define HAVE_SZ 1

/* Define to 1 if you have the <hdf5.h> header file. */
#define HAVE_HDF5_H 1

/* Define to 1 if you have the <hdf5.h> header file. */
/* #undef HAVE_HDF5_HL_H */

/* Define to 1 if the system has the type `int64'. */
/* #undef HAVE_INT64 */

/* Define to 1 if you have the <inttypes.h> header file. */
#define HAVE_INTTYPES_H 1

/* Define to 1 if you have the `dl' library (-ldl). */
/* #undef HAVE_LIBDL */

/* Define to 1 if you have the `jpeg' library (-ljpeg). */
/* #undef HAVE_LIBJPEG */

/* Define to 1 if you have the `m' library (-lm). */
#define HAVE_LIBM 1

/* Define to 1 if you have the `mfhdf' library (-lmfhdf). */
/* #undef HAVE_LIBMFHDF */

/* Define to 1 if you have the `pnetcdf' library (-lpnetcdf). */
/* #undef HAVE_LIBPNETCDF */

/* Define to 1 if you have the libxml2 library. */
#define ENABLE_LIBXML2 1

/* Define to 1 if you have the <locale.h> header file. */
#define HAVE_LOCALE_H 1

/* Define to 1 if the system has the type `longlong'. */
/* #undef HAVE_LONGLONG */

/* Define to 1 if the system has the type 'long long int'. */
#define HAVE_LONG_LONG_INT 1

/* Define to 1 if you have the <malloc.h> header file. */
#define HAVE_MALLOC_H 1

/* Define to 1 if you have the `memmove' function. */
#define HAVE_MEMMOVE 1

/* Define to 1 if you have the `mkstemp' function. */
#define HAVE_MKSTEMP 1

/* Define to 1 if you have the `mktemp' function. */
#define HAVE_MKTEMP 1

/* Define to 1 if you have the `MPI_Comm_f2c' function. */
/* #undef HAVE_MPI_COMM_F2C */

/* Define to 1 if you have the `MPI_Info_f2c' function. */
/* #undef HAVE_MPI_INFO_F2C */

/* Define to 1 if you have the `mremap' function. */
#define HAVE_MREMAP 1

/* Define to 1 if you have the `random' function. */
#define HAVE_RANDOM 1

/* Define to 1 if you have the `snprintf' function. */
#define HAVE_SNPRINTF 1

/* Define to 1 if the system has the type `ssize_t'. */
#define HAVE_SSIZE_T 1

/* Define to 1 if the system has the type `ptrdiff_t'. */
#define HAVE_PTRDIFF_T 1

/* Define to 1 if the system has the type `uintptr_t'. */
#define HAVE_UINTPTR_T 1

/* Define to 1 if you have the <stdarg.h> header file. */
#define HAVE_STDARG_H 1

/* Define to 1 if you have the <stdint.h> header file. */
#define HAVE_STDINT_H 1

/* Define to 1 if you have the <stdio.h> header file. */
#define HAVE_STDIO_H 1

/* Define to 1 if you have the <stdlib.h> header file. */
#define HAVE_STDLIB_H 1

/* Define to 1 if you have the <strings.h> header file. */
#define HAVE_STRINGS_H 1

/* Define to 1 if you have the <signal.h> header file. */
#define HAVE_SIGNAL_H 1

/* Define to 1 if you have the <string.h> header file. */
#define HAVE_STRING_H 1

/* Define to 1 if you have the <ftw.h> header file. */
#define HAVE_FTW_H 1

/* Define to 1 if you have the <libgen.h> header file. */
#define HAVE_LIBGEN_H 1

/* Define to 1 if you have the `strdup' function. */
#define HAVE_STRDUP 1

/* Define to 1 if you have the `strndup` function. */
#define HAVE_STRNDUP

/* Define to 1 if you have the `strcasecmp` function. */
#define HAVE_STRCASECMP

/* Define to 1 if you have the `strlcat' function. */
/* #undef HAVE_STRLCAT */

/* Define to 1 if you have the `strtoll' function. */
#define HAVE_STRTOLL 1

/* Define to 1 if you have the `strtoull' function. */
#define HAVE_STRTOULL 1

/* Define to 1 if you have the `stroull' function. */
/* #undef HAVE_STROULL */

/* Define to 1 if `st_blksize' is a member of `struct stat'. */
/* #undef HAVE_STRUCT_STAT_ST_BLKSIZE */

/* Define to 1 if you have the `sysconf' function. */
#define HAVE_SYSCONF 1

/* Define to 1 if you have the <sys/param.h> header file. */
#define HAVE_SYS_PARAM_H 1

/* Define to 1 if you have the <sys/resource.h> header file. */
#define HAVE_SYS_RESOURCE_H 1

/* Define to 1 if you have the <sys/stat.h> header file. */
#define HAVE_SYS_STAT_H 1

/* Define to 1 if you have the <sys/time.h> header file. */
#define HAVE_SYS_TIME_H 1

/* Define to 1 if you have the <sys/types.h> header file. */
#define HAVE_SYS_TYPES_H 1

/* Define to 1 if you have the <time.h> header file. */
#define HAVE_TIME_H 1

/* Define to 1 if the system has the type `uchar'. */
/* #undef HAVE_UCHAR */

/* Define to 1 if the system has the type `uint'. */
#define HAVE_UINT 1

/* Define to 1 if the system has the type `uint64'. */
/* #undef HAVE_UINT64 */

/* Define to 1 if the system has the type `uint64_t'. */
#define HAVE_UINT64_T 1

/* Define to 1 if you have the <unistd.h> header file. */
#define HAVE_UNISTD_H 1
/* #undef YY_NO_UNISTD_H */

/* Define to 1 if the system has the type `ushort'. */
#define HAVE_USHORT 1

/* if true, hdf5 has parallelism enabled */
/* #undef HDF5_PARALLEL */

/* if true, HDF5 is at least version 1.10. 3 and allows parallel I/O
with zip */
#define HDF5_SUPPORTS_PAR_FILTERS 1

/* if true, HDF5 is at least version 1.10.5 and supports UTF8 paths */
/* #undef HDF5_UTF8_PATHS */

/* if true, include JNA bug fix */
/* #undef JNA */

/* do large file tests */
/* #undef LARGE_FILE_TESTS */

/* If true, turn on logging. */
/* #undef LOGGING */

/* If true, define nc_set_log_level. */
#define ENABLE_SET_LOG_LEVEL 1

/* max size of the default per-var chunk cache. */
#define MAX_DEFAULT_CACHE_SIZE 67108864

/* min blocksize for posixio. */
#define NCIO_MINBLOCKSIZE 256

/* Add extra properties to _NCProperties attribute */
/* #undef NCPROPERTIES_EXTRA */

/* Idspatch table version */
#define NC_DISPATCH_VERSION 5

/* no IEEE float on this platform */
/* #undef NO_IEEE_FLOAT */

#define BUILD_V2 1
/* #undef ENABLE_DOXYGEN */
/* #undef ENABLE_INTERNAL_DOCS */
/* #undef VALGRIND_TESTS */
/* #undef ENABLE_CDMREMOTE */
#define USE_HDF5 1
/* #undef ENABLE_FILEINFO */
/* #undef TEST_PARALLEL */
/* #undef BUILD_RPC */
/* #undef USE_X_GETOPT */
#define ENABLE_EXTREME_NUMBERS 1

/* do not build the netCDF version 2 API */
/* #undef NO_NETCDF_2 */

/* Name of package */
#define PACKAGE "netcdf"

/* Define to the address where bug reports for this package should be sent. */
#define PACKAGE_BUGREPORT "support-netcdf@unidata.ucar.edu"

/* Define to the full name of this package. */
#define PACKAGE_NAME "netCDF"

/* Define to the full name and version of this package. */
#define PACKAGE_STRING "netCDF 4.9.0"

/* Define to the one symbol short name of this package. */
#define PACKAGE_TARNAME "netcdf"

/* Define to the home page for this package. */
#define PACKAGE_URL ""

/* Define to the version of this package. */
#define PACKAGE_VERSION "4.9.0"

/* Do we have access to the Windows Registry */
/* #undef REGEDIT */

/* define the possible sources for remote test servers */
#define REMOTETESTSERVERS	"remotetest.unidata.ucar.edu"

/* The size of `ulonglong` as computed by sizeof. */
#define SIZEOF_ULONGLONG 8

/* The size of `longlong` as computed by sizeof. */
#define SIZEOF_LONGLONG 8

/* The size of `char` as computed by sizeof. */
#define SIZEOF_CHAR 1

/* The size of `uchar` as computed by sizeof. */
#define SIZEOF_UCHAR 1

/* The size of `__int64` found on Windows systems. */
/* #undef SIZEOF___INT64 */

/* The size of `void*` as computed by sizeof. */
#define SIZEOF_VOIDSTAR 8

/* The size of `short` as computed by sizeof. */
#define SIZEOF_OFF64_T 8

/* The size of `double', as computed by sizeof. */
#define SIZEOF_DOUBLE 8

/* The size of `float', as computed by sizeof. */
#define SIZEOF_FLOAT 4

/* The size of `int', as computed by sizeof. */
#define SIZEOF_INT 4

/* The size of `long', as computed by sizeof. */
#define SIZEOF_LONG 8

/* The size of `long long', as computed by sizeof. */
#define SIZEOF_LONG_LONG 8

/* The size of `off_t', as computed by sizeof. */
#define SIZEOF_OFF_T 8

/* The size of `short', as computed by sizeof. */
#define SIZEOF_SHORT 2

/* The size of `size_t', as computed by sizeof. */
#define SIZEOF_SIZE_T 8

/* The size of `uint', as computed by sizeof. */
#define SIZEOF_UINT 4

/* The size of `unsigned int', as computed by sizeof. */
#define SIZEOF_UNSIGNED_INT 4

/* The size of `unsigned long long', as computed by sizeof. */
#define SIZEOF_UNSIGNED_LONG_LONG 8

/* The size of `unsigned short int', as computed by sizeof. */
#define SIZEOF_UNSIGNED_SHORT_INT 2

/* The size of `ushort', as computed by sizeof. */
#define SIZEOF_USHORT 2

/* The size of `void*', as computed by sizeof. */
#define SIZEOF_VOIDP 8

/* Place to put very large netCDF test files. */
#define TEMP_LARGE "."

/* if true, build DAP Client */
/* #undef USE_DAP */

/* if true, include NC_DISKLESS code */
/* #undef USE_DISKLESS */

/* set this to use extreme numbers in tests */
#define USE_EXTREME_NUMBERS 1

/* if true, use ffio instead of posixio */
/* #undef USE_FFIO */

/* if true, include experimental fsync code */
/* #undef USE_FSYNC */

/* if true, use HDF4 too */
/* #undef USE_HDF4 */

/* If true, use use wget to fetch some sample HDF4 data, and then test against
   it. */
/* #undef USE_HDF4_FILE_TESTS */

/* if true, use mmap for in-memory files */
#define USE_MMAP 1

/* if true, build netCDF-4 */
#define USE_NETCDF4 1

/* build the netCDF version 2 API */
#define USE_NETCDF_2 1

/* if true, pnetcdf or parallel netcdf-4 is in use */
/* #undef USE_PARALLEL */

/* if true, parallel netcdf-4 is in use */
/* #undef USE_PARALLEL4 */

/* if true, parallel netCDF is used */
/* #undef USE_PNETCDF */

/* if true, use stdio instead of posixio */
/* #undef USE_STDIO */

/* if true, multi-filters enabled*/
#define ENABLE_MULTIFILTERS 1

/* if true, enable nczarr blosc support */
/* #undef ENABLE_BLOSC */

/* Version number of package */
#define VERSION "4.9.0"

/* Capture  Windows version and build */
/* #undef WINVERMAJOR */
/* #undef WINVERBUILD */

/* Define WORDS_BIGENDIAN to 1 if your processor stores words with the most
   significant byte first (like Motorola and SPARC, unlike Intel). */
#if defined AC_APPLE_UNIVERSAL_BUILD
# if defined __BIG_ENDIAN__
#  define WORDS_BIGENDIAN 1
# endif
#else
# ifndef WORDS_BIGENDIAN
/* #undef WORDS_BIGENDIAN */
# endif
#endif

/* Enable large inode numbers on Mac OS X 10.5.  */
#ifndef _DARWIN_USE_64_BIT_INODE
# define _DARWIN_USE_64_BIT_INODE 1
#endif

/* Define for large files, on AIX-style hosts. */
/* #undef _LARGE_FILES */

/* Define to `long int' if <sys/types.h> does not define. */
/* #undef off_t */

/* Define to `unsigned int' if <sys/types.h> does not define. */
/* #undef size_t */

/* Define to `int' if <sys/types.h> does not define. */
/* #undef ssize_t */

/* Define to `signed long if <sys/types.h> does not define. */
/* #undef ptrdiff_t */

/* Define to `unsigned long if <sys/types.h> does not define. */
/* #undef uintptr_t */

/* #undef WORDS_BIGENDIAN */

#include "ncconfigure.h"

#endif

EOF""",
)
