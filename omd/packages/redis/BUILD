load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "bin_pkg",
    srcs = [
        "@redis//:build",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "redis-check-aof",
    link_name = "bin/redis-check-aof",
    target = "redis-server",
)

pkg_mklink(
    name = "redis-check-rdb",
    link_name = "bin/redis-check-rdb",
    target = "redis-server",
)

pkg_mklink(
    name = "redis-sentinel",
    link_name = "bin/redis-sentinel",
    target = "redis-server",
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/logrotate.d/redis",
        "skel/etc/redis/redis.conf",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = [
        "skel/etc/init.d/redis",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "40-redis",
    link_name = "skel/etc/rc.d/40-redis",
    target = "../init.d/redis",
)

pkg_mkdirs(
    name = "skel_var",
    dirs = [
        "skel/var/redis",
    ],
)

pkg_tar(
    name = "redis",
    srcs = [
        "redis-check-rdb",
        "redis-sentinel",
        ":40-redis",
        ":bin_pkg",
        ":redis-check-aof",
        ":skel",
        ":skel_755",
        ":skel_var",
    ],
    visibility = ["//omd:__pkg__"],
)
