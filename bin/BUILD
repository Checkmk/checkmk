load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary")

#
# Don't add new stuff to this file!
#
# See doc/documentation/arch-migrations.rst
#

cc_binary(
    name = "mkevent",
    srcs = ["mkevent.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["no-lint"],
)

cc_binary(
    name = "mkeventd_open514",
    srcs = ["mkeventd_open514.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["no-lint"],
)

pkg_files(
    name = "bin_750",
    srcs = [
        ":mkeventd_open514",
    ],
    attributes = pkg_attributes(
        mode = "0750",
    ),
    prefix = "bin",
)

pkg_files(
    name = "bin_755",
    srcs = [
        ":cmk-generate-api-spec",
        ":mkevent",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":bin_750",
        ":bin_755",
    ],
    stamp = 1,
    visibility = ["//visibility:public"],
)

sh_library(
    name = "bin_sh",
    srcs = [
        ".f12",
        "apply_unsign_msi_patch.sh",
    ],
)
