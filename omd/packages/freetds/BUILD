load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_filegroup", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath_tree")

filegroup(
    name = "freetds_gen_dir",
    srcs = ["@freetds"],
    output_group = "gen_dir",
    tags = ["manual"],
)

directory_path(
    name = "freetds_include_dir",
    directory = ":freetds_gen_dir",
    path = "include",
    tags = ["manual"],
)

copy_to_directory(
    name = "freetds_include",
    srcs = [":freetds_include_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/freetds"],
    tags = ["manual"],
)

pkg_files(
    name = "freetds_include_files",
    srcs = [
        ":freetds_include",
    ],
    strip_prefix = strip_prefix.from_pkg("freetds_include"),
    tags = ["manual"],
)

directory_path(
    name = "freetds_lib_dir",
    directory = ":freetds_gen_dir",
    path = "lib",
    tags = ["manual"],
)

copy_to_directory(
    name = "freetds_lib_copy",
    srcs = [":freetds_lib_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/lib"],
    tags = ["manual"],
)

set_runpath_tree(
    name = "freetds_lib_deployable",
    src = ":freetds_lib_copy",
    rpath = "$ORIGIN",
    tags = ["manual"],
)

filter_directory(
    name = "freetds_lib_no_symlinks",
    src = "freetds_lib_deployable",
    excludes = [
        "libct.so",
        "libct.so.4",
        "libsybdb.so",
        "libsybdb.so.5",
    ],
    tags = ["manual"],
)

pkg_files(
    name = "freetds_lib_files",
    srcs = [
        ":freetds_lib_no_symlinks",
    ],
    strip_prefix = strip_prefix.from_pkg("freetds_lib_no_symlinks"),
    tags = ["manual"],
)

# target_name -> target
symlinks = [
    (
        "libct.so",
        "libct.so.4.0.0",
    ),
    (
        "libct.so.4",
        "libct.so.4.0.0",
    ),
    (
        "libsybdb.so",
        "libsybdb.so.5.1.0",
    ),
    (
        "libsybdb.so.5",
        "libsybdb.so.5.1.0",
    ),
]

pkg_filegroup(
    name = "freetds_lib_pkg",
    srcs = [
        ":freetds_lib_files",
    ] + [i[0] for i in symlinks],
    prefix = "lib",
    tags = ["manual"],
)

[pkg_mklink(
    name = link_name,
    link_name = link_name,
    tags = ["manual"],
    target = target,
) for link_name, target in symlinks]

pkg_filegroup(
    name = "freetds_pkg",
    srcs = [
        ":freetds_include_files",
        ":freetds_lib_pkg",
    ],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "freetds_tar",
    srcs = [
        ":freetds_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
