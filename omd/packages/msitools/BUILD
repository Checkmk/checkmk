load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")

exclude_from_filegroup(
    name = "msitools_rest",
    src = "@msitools//:gen_dir",
    excludes = ["bin/*"],
)

pkg_files(
    name = "msitools_rest_pkg",
    srcs = [
        ":msitools_rest",
    ],
    strip_prefix = "rest",
)

pkg_files(
    name = "msitools_bin",
    srcs = [
        "@msitools//:msibuild",
        "@msitools//:msiinfo",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "msitools",
    srcs = [
        ":msitools_bin",
        ":msitools_rest_pkg",
    ],
    visibility = ["//visibility:public"],
)
