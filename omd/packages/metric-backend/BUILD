load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
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

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":clickhouse_bin_pkg",
    ],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
