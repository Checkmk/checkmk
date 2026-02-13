load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath", "set_soname")

set_soname(
    name = "libsnap7_soname",
    srcs = ["@snap7//:libsnap7.so"],
    tags = ["manual"],
)

set_runpath(
    name = "libsnap7_runpath",
    srcs = [":libsnap7_soname"],
    tags = ["manual"],
)

pkg_files(
    name = "lib_pkg",
    srcs = [
        ":libsnap7_runpath",
    ],
    prefix = "lib",
    tags = ["manual"],
)

pkg_tar(
    name = "snap7",
    srcs = [
        ":lib_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
