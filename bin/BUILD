load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

#
# Don't add new stuff to this file!
#
# See doc/documentation/arch-migrations.rst
#

pkg_tar(
    name = "pkg_tar",
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
