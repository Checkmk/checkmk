load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

#
# Don't add new stuff to this file!
#
# See doc/documentation/arch-migrations.rst
#

pkg_files(
    name = "bin_755",
    srcs = [
        ":cmk-generate-api-spec",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
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
