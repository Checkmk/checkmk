load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "lib_pkg",
    srcs = [
        "@mod_fcgid//:mod_fcgid.so",
    ],
    prefix = "lib/apache/modules",
    tags = ["manual"],
)

pkg_files(
    name = "skel_pkg",
    srcs = [
        ":skel/etc/apache/conf.d/02_fcgid.conf",
    ],
    prefix = "skel/etc/apache/conf.d",
    tags = ["manual"],
)

pkg_tar(
    name = "mod_fcgid",
    srcs = [
        ":lib_pkg",
        ":skel_pkg",
    ],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
