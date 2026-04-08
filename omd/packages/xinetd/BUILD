load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

directory_path(
    name = "xinetd_share_dir",
    directory = "@xinetd//:gen_dir",
    path = "share",
    tags = ["manual"],
)

directory_path(
    name = "xinetd_etc_dir",
    directory = "@xinetd//:gen_dir",
    path = "etc",
    tags = ["manual"],
)

copy_to_directory(
    name = "xinetd_share_copy",
    srcs = [":xinetd_share_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/share"],
    tags = ["manual"],
)

copy_to_directory(
    name = "xinetd_etc_copy",
    srcs = [":xinetd_etc_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/etc"],
    tags = ["manual"],
)

pkg_files(
    name = "share",
    srcs = [":xinetd_share_copy"],
    prefix = "share",
    strip_prefix = "xinetd_share_copy",
    tags = ["manual"],
)

pkg_files(
    name = "etc",
    srcs = [":xinetd_etc_copy"],
    prefix = "etc",
    strip_prefix = "xinetd_etc_copy",
    tags = ["manual"],
)

set_runpath(
    name = "xinetd_bin_runpath",
    srcs = ["@xinetd//:xinetd_bin"],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "xinetd_bin",
    srcs = [":xinetd_bin_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_tar(
    name = "xinetd",
    srcs = [
        ":etc",
        ":share",
        ":xinetd_bin",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
