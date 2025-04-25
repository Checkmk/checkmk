load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "lcab_bin",
    srcs = ["@lcab//:lcab_bin"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "lcab",
    srcs = [
        "lcab_bin",
    ],
    visibility = ["//omd:__pkg__"],
)
