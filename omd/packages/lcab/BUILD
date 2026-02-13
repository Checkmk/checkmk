load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

set_runpath(
    name = "lcab_runpath",
    srcs = ["@lcab//:lcab_bin"],
    rpaths = ["${ORIGIN}/../lib"],
)

pkg_files(
    name = "lcab_bin",
    srcs = [":lcab_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_tar(
    name = "lcab",
    srcs = [
        "lcab_bin",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
