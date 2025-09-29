load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "clickhouse_bin_pkg",
    srcs = ["@clickhouse"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_mklink(
    name = "clickhouse-server",
    link_name = "bin/clickhouse-server",
    tags = ["manual"],
    target = "./clickhouse",
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/clickhouse-server/config.xml",
        "skel/etc/clickhouse-server/users.xml",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

pkg_mkdirs(
    name = "skel_dirs",
    dirs = [
        "skel/var/log/clickhouse-server",
        "skel/var/lib/clickhouse-server",
        "skel/etc/clickhouse-server/conf.d",
    ],
    tags = ["manual"],
)

pkg_files(
    name = "skel_755",
    srcs = [
        "skel/etc/init.d/clickhouse",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

pkg_mklink(
    name = "92-clickhouse",
    link_name = "skel/etc/rc.d/92-clickhouse",
    tags = ["manual"],
    target = "../init.d/clickhouse",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":92-clickhouse",
        ":clickhouse-server",
        ":clickhouse_bin_pkg",
        ":skel",
        ":skel_755",
        ":skel_dirs",
    ],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
