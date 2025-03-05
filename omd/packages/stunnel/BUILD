load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "bin_pkg",
    srcs = [
        "@stunnel//:stunnel3_bin",
        "@stunnel//:stunnel_bin",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
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
)

pkg_files(
    name = "lib_pkg",
    srcs = [
        "@stunnel//:libstunnel.so",
    ],
    prefix = "lib/stunnel",
)

pkg_files(
    name = "skel_640_pkg",
    srcs = [
        "skel/etc/logrotate.d/stunnel",
        "skel/etc/stunnel/server.conf",
    ],
    attributes = pkg_attributes(
        mode = "0640",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mkdirs(
    name = "conf.d",
    dirs = ["skel/etc/stunnel/conf.d"],
)

pkg_mklink(
    name = "85-stunnel",
    link_name = "skel/etc/rc.d/85-stunnel",
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
)

pkg_filegroup(
    name = "skel",
    srcs = [
        "skel_640_pkg",
        "skel_755_pkg",
        ":85-stunnel",
        ":conf.d",
    ],
)

pkg_tar(
    name = "stunnel",
    srcs = [
        ":bash_completion",
        ":bin_pkg",
        ":lib_pkg",
        ":skel",
    ],
    visibility = ["//omd:__pkg__"],
)
