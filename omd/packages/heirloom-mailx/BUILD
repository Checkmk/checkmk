load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

set_runpath(
    name = "mailx_runpath",
    srcs = ["@heirloom-mailx//:mailx"],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "bin_pkg",
    srcs = [
        ":mailx_runpath",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {":mailx_runpath": "heirloom-mailx"},
    tags = ["manual"],
)

pkg_mklink(
    name = "mailx_link",
    link_name = "bin/mail",
    tags = ["manual"],
    target = "./heirloom-mailx",
)

pkg_tar(
    name = "mailx.1",
    srcs = [
        "@heirloom-mailx//:share",
    ],
    extension = "tar.gz",
    package_file_name = "share/man/man1/heirloom-mailx.1.gz",
    stamp = 1,
    tags = ["manual"],
)

pkg_files(
    name = "share_pkg",
    srcs = [
        ":mailx.1",
    ],
    prefix = "share/man/man1",
    tags = ["manual"],
)

pkg_files(
    name = "skel_pkg",
    srcs = ["skel/etc/mail.rc"],
    prefix = "skel/etc",
    tags = ["manual"],
)

pkg_tar(
    name = "heirloom-mailx",
    srcs = [
        "skel_pkg",
        ":bin_pkg",
        ":mailx_link",
        ":share_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
