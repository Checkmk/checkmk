load("@//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exclude_from_filegroup(
    name = "xinetd_rest",
    src = "@xinetd//:gen_dir",
    excludes = [
        "bin/*",
        "sbin",
    ],
)

pkg_files(
    name = "share",
    srcs = [
        "xinetd_rest",
    ],
    strip_prefix = "rest",
)

pkg_files(
    name = "xinetd_bin",
    srcs = [
        "@xinetd//:xinetd_bin",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "xinetd",
    srcs = [
        ":share",
        ":xinetd_bin",
    ],
    visibility = ["//omd:__pkg__"],
)
