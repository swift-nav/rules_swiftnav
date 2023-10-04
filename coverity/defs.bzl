# Copyright (c) 2022 Synopsys, Inc. All rights reserved worldwide.
load("//coverity/private:gen_script.bzl", "gen_script")
load("//coverity/private:compile_mnemonics.bzl", "compile_mnemonics")
load("//coverity/private:link_mnemonics.bzl", "link_mnemonics")
load("//coverity/private:enable_link.bzl", "enable_link")
cov_gen_script = gen_script
cov_compile_mnemonics = compile_mnemonics
cov_link_mnemonics = link_mnemonics
cov_enable_link = enable_link
