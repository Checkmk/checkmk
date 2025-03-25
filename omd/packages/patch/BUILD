load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "patch_bin_pkg",
    srcs = ["@patch//:bin/patch"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "patch_man_pkg",
    srcs = ["@patch//:share/man/man1/patch.1"],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_tar(
    name = "patch",
    srcs = [
        ":patch_bin_pkg",
        ":patch_man_pkg",
    ],
    visibility = ["//omd:__pkg__"],
)
