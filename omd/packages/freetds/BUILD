load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_filegroup", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("//bazel/rules:make_deployable.bzl", "make_deployable_dir")

exclude_from_filegroup(
    name = "freetds_include",
    src = "@freetds//:gen_dir",
    excludes = [
        "share",
        "etc",
        "lib",
    ],
)

pkg_files(
    name = "freetds_include_files",
    srcs = [
        ":freetds_include",
    ],
    strip_prefix = strip_prefix.from_pkg("rest"),
)

make_deployable_dir(
    name = "freetds_lib_deployable",
    src = "@freetds//:gen_dir",
    input_dir = "lib",
    rpath = "\\$ORIGIN",
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
)

pkg_files(
    name = "freetds_lib_files",
    srcs = [
        ":freetds_lib_no_symlinks",
    ],
    strip_prefix = strip_prefix.from_pkg("freetds_lib_no_symlinks"),
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
)

[pkg_mklink(
    name = link_name,
    link_name = link_name,
    target = target,
) for link_name, target in symlinks]

pkg_filegroup(
    name = "freetds_pkg",
    srcs = [
        ":freetds_include_files",
        ":freetds_lib_pkg",
    ],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "freetds_tar",
    srcs = [
        ":freetds_pkg",
    ],
    visibility = ["//visibility:public"],
)
