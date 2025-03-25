load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "lib_pkg",
    srcs = [
        "@snap7//:libsnap7.so",
    ],
    prefix = "lib",
)

pkg_tar(
    name = "snap7",
    srcs = [
        ":lib_pkg",
    ],
    visibility = ["//omd:__pkg__"],
)
