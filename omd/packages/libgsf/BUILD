load("@//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exclude_from_filegroup(
    name = "libgsf_rest",
    src = "@libgsf//:gen_dir",
    excludes = ["bin/*"],
    tags = ["manual"],
)

pkg_files(
    name = "libgsf_without_bin",
    srcs = [
        "libgsf_rest",
    ],
    strip_prefix = "rest",
    tags = ["manual"],
)

pkg_files(
    name = "libgsf_bin",
    srcs = [
        "@libgsf//:gsf",
        "@libgsf//:gsf-office-thumbnailer",
        "@libgsf//:gsf-vba-dump",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_tar(
    name = "libgsf",
    srcs = [
        ":libgsf_bin",
        ":libgsf_without_bin",
    ],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
