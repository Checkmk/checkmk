load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

exports_files(["skel.permissions"])

set_runpath(
    name = "bin_runpath",
    srcs = [
        "@stunnel//:stunnel_bin",
    ],
    rpaths = ["${ORIGIN}/../lib"],
)

pkg_files(
    name = "bin_pkg",
    srcs = [
        ":bin_runpath",
        "@stunnel//:stunnel3_bin",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

set_runpath(
    name = "lib_runpath",
    srcs = ["@stunnel//:libstunnel.so"],
)

pkg_files(
    name = "lib_pkg",
    srcs = [":lib_runpath"],
    prefix = "lib/stunnel",
    tags = ["manual"],
)

pkg_files(
    name = "bash_completion",
    srcs = [
        "@stunnel//:stunnel.bash",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "skel/etc/bash_completion.d",
    tags = ["manual"],
)

pkg_files(
    name = "skel_pkg",
    srcs = [
        "skel/etc/logrotate.d/stunnel",
        "skel/etc/stunnel/server.conf",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

pkg_mkdirs(
    name = "conf.d",
    dirs = ["skel/etc/stunnel/conf.d"],
    tags = ["manual"],
)

pkg_mklink(
    name = "85-stunnel",
    link_name = "skel/etc/rc.d/85-stunnel",
    tags = ["manual"],
    target = "../init.d/stunnel",
)

pkg_files(
    name = "skel_755_pkg",
    srcs = [
        "skel/etc/init.d/stunnel",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

pkg_filegroup(
    name = "skel",
    srcs = [
        "skel_755_pkg",
        "skel_pkg",
        ":85-stunnel",
        ":conf.d",
    ],
    tags = ["manual"],
)

pkg_tar(
    name = "stunnel",
    srcs = [
        ":bash_completion",
        ":bin_pkg",
        ":lib_pkg",
        ":skel",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)

sh_library(
    name = "omd_packages_stunnel_sh",
    srcs = [
        "skel/etc/init.d/stunnel",
    ],
)
