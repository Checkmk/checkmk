load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "clickhouse_bin_pkg",
    srcs = ["@clickhouse"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
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

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":clickhouse_bin_pkg",
        ":skel",
        ":skel_dirs",
    ],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
