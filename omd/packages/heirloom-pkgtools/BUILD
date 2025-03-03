load("@//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "bin_pkg",
    srcs = [
        "@heirloom-pkgtools//:pkgmk",
        "@heirloom-pkgtools//:pkgtrans",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

exclude_from_filegroup(
    name = "share",
    src = "@heirloom-pkgtools//:share",
    excludes = ["bin"],
)

pkg_files(
    name = "share_pkg",
    srcs = [
        ":share",
    ],
    strip_prefix = "rest",
)

pkg_tar(
    name = "heirloom-pkgtools",
    srcs = [
        "bin_pkg",
        "share_pkg",
    ],
    visibility = ["//visibility:public"],
)
