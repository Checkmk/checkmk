load("@//bazel/rules:filtered_subdir.bzl", "filtered_subdir")
load("@//bazel/rules:make_deployable.bzl", "string_replace")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "skel_pkg",
    srcs = glob(
        ["skel/**/*"],
        exclude = [
            "skel/etc/rc.d/**",
            "**/.gitignore",
        ],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

pkg_mklink(
    name = "50-npcd",
    link_name = "skel/etc/rc.d/50-npcd",
    tags = ["manual"],
    target = "../init.d/npcd",
)

pkg_mklink(
    name = "52-pnp_gearman_worker",
    link_name = "skel/etc/rc.d/52-pnp_gearman_worker",
    tags = ["manual"],
    target = "../init.d/pnp_gearman_worker",
)

pkg_files(
    name = "PNP4NAGIOS_pkg",
    srcs = ["PNP4NAGIOS"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/omd/hooks",
    tags = ["manual"],
)

filegroup(
    name = "bin_filegroup",
    srcs = ["@pnp4nagios//:build"],
    output_group = "npcd",
    tags = ["manual"],
)

pkg_files(
    name = "bin_pkg",
    srcs = [":bin_filegroup"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "bin",
    tags = ["manual"],
)

filegroup(
    name = "gen_dir_filegroup",
    srcs = ["@pnp4nagios//:build"],
    output_group = "gen_dir",
    tags = ["manual"],
)

filtered_subdir(
    name = "lib_filegroup",
    src = ":gen_dir_filegroup",
    excludes = ["kohana/"],
    subdir = "lib",
    tags = ["manual"],
)

string_replace(
    name = "lib_with_omdroot_filegroup",
    src = ":lib_filegroup",
    filepattern = ["*.pl"],
    replace_labels = {
        "cmk_version": "@cmk//version",
        "cmk_edition": "@cmk//edition",
    },
    replace_pattern = "__OMD_ROOT__",
    tags = ["manual"],
    value = "/omd/versions/{cmk_version}.{cmk_edition}",
)

pkg_files(
    name = "lib_pkg",
    srcs = [":lib_with_omdroot_filegroup"],
    attributes = pkg_attributes(mode = "0755"),
    strip_prefix = strip_prefix.from_pkg("lib_with_omdroot_filegroup"),
    tags = ["manual"],
)

filtered_subdir(
    name = "man_filegroup",
    src = ":gen_dir_filegroup",
    subdir = "man",
    tags = ["manual"],
)

pkg_files(
    name = "man_pkg",
    srcs = [":man_filegroup"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "share",
    tags = ["manual"],
)

filtered_subdir(
    name = "doc_filegroup",
    src = ":gen_dir_filegroup",
    subdir = "doc/pnp4nagios",
    tags = ["manual"],
)

pkg_files(
    name = "doc_pkg",
    srcs = [":doc_filegroup"],
    prefix = "share/doc",
    tags = ["manual"],
)

pkg_files(
    name = "diskspace_pkg",
    srcs = ["diskspace"],
    renames = {"diskspace": "share/diskspace/pnp4nagios"},
    tags = ["manual"],
)

pkg_mkdirs(
    name = "emptydirs_pkg",
    dirs = [
        "include",
        "skel/var/pnp4nagios/log",
        "skel/var/pnp4nagios/perfdata",
        "skel/var/pnp4nagios/stats",
        "skel/var/pnp4nagios/spool",
        "skel/tmp/pnp4nagios/lock",
        "skel/tmp/pnp4nagios/run",
        "skel/tmp/pnp4nagios/stats",
        "skel/etc/pnp4nagios/config.d",
    ],
    tags = ["manual"],
)

pkg_tar(
    name = "pnp4nagios",
    srcs = [
        ":50-npcd",
        ":52-pnp_gearman_worker",
        ":PNP4NAGIOS_pkg",
        ":bin_pkg",
        ":diskspace_pkg",
        ":doc_pkg",
        ":emptydirs_pkg",
        ":lib_pkg",
        ":man_pkg",
        ":skel_pkg",
    ],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
