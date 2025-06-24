load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "cpp-libs-pkg",
    srcs = [
        "@cpp_libs",
    ],
    prefix = "lib",
)

pkg_tar(
    name = "cpp-libs",
    srcs = [
        "cpp-libs-pkg",
    ],
    visibility = ["//visibility:public"],
)
