load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
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
    tags = ["manual"],
)

directory_path(
    name = "heirloom_share_dir",
    directory = "@heirloom-pkgtools//:share",
    path = "share",
    tags = ["manual"],
)

copy_to_directory(
    name = "share_copy",
    srcs = [":heirloom_share_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/heirloom-pkgtools"],
    tags = ["manual"],
)

pkg_files(
    name = "share_pkg",
    srcs = [
        ":share_copy",
    ],
    strip_prefix = "share_copy",
    tags = ["manual"],
)

pkg_tar(
    name = "heirloom-pkgtools",
    srcs = [
        "bin_pkg",
        "share_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
