load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "lib_pkg",
    srcs = [
        "@mod_wsgi//:mod_wsgi.so",
    ],
    prefix = "lib/apache/modules",
)

pkg_files(
    name = "skel_pkg",
    srcs = [
        ":skel/etc/apache/conf.d/01_wsgi.conf",
    ],
    prefix = "skel/etc/apache/conf.d",
)

pkg_tar(
    name = "mod_wsgi",
    srcs = [
        ":lib_pkg",
        ":skel_pkg",
    ],
    visibility = ["//omd:__pkg__"],
)
